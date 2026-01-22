from django.shortcuts import render, redirect, get_object_or_404
from .models import TontineGroup, Membership, Transaction, HistoriqueGagnant
from django.contrib.auth.decorators import login_required
import random
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from decimal import Decimal
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
import requests # Pour parler à l'API de Campay
from django.conf import settings # Pour lire tes clés dans settings.py

# 1. ACCUEIL
def home(request):
    return render(request, 'tontine/index.html')


# 2. INVITATION
@login_required
def rejoindre_via_lien(request, groupe_id):
    groupe = get_object_or_404(TontineGroup, id=groupe_id)
    membership, created = Membership.objects.get_or_create(
        user=request.user,
        group=groupe,
        defaults={'is_verified': False}
    )
    return render(request, 'tontine/detail_invitation.html', {'groupe': groupe})


# 3. INSCRIPTION
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# 4. PAIEMENT AUTOMATISÉ
@login_required
def submit_payment(request, group_id):
    if request.method == "POST":
        reference = request.POST.get('reference')
        amount = request.POST.get('amount')
        group = get_object_or_404(TontineGroup, id=group_id)
        membership = get_object_or_404(Membership, user=request.user, group=group)

        Transaction.objects.create(
            membership=membership,
            amount=amount,
            reference_api=reference,
            is_confirmed=True
        )

        membership.is_verified = True
        membership.save()

        messages.success(request, "Dépôt réussi ! Vous êtes maintenant actif.")
    return redirect('mon_espace')


# 5. ESPACE MEMBRE
@login_required
def mon_espace(request):
    participations = Membership.objects.filter(user=request.user)
    return render(request, 'tontine/mon_espace.html', {'participations': participations})


# 6. DASHBOARD ADMIN
@login_required
def tableau_bord_admin(request):
    # On ne montre que les groupes créés par l'utilisateur connecté
    mes_groupes = TontineGroup.objects.filter(admin_groupe=request.user)
    if not mes_groupes.exists() and not request.user.is_staff:
        messages.error(request, "Vous n'avez pas accès au Dashboard Admin.")
        return redirect('mon_espace')

    return render(request, 'tontine/admin_dashboard.html', {'mes_groupes': mes_groupes
    })


# 7. GESTION DES GROUPES
@login_required
def detail_groupe(request, groupe_id):
    groupe = get_object_or_404(TontineGroup, id=groupe_id, admin_groupe=request.user)
    membres = Membership.objects.filter(group=groupe)

    nb_paye = membres.filter(is_verified=True).count()
    caisse_totale = nb_paye * groupe.contribution_amount

    groupe.caisse_totale = caisse_totale
    groupe.save()

    montant_base = groupe.contribution_amount
    frais_depot = montant_base * Decimal('0.03')
    total_a_payer = montant_base + frais_depot

    ta_commission = caisse_totale * Decimal('0.02')
    gain_net_gagnant = caisse_totale - ta_commission

    context = {
        'groupe': groupe,
        'membres': membres,
        'frais_depot': frais_depot,
        'total_a_payer': total_a_payer,
        'ta_commission': ta_commission,
        'gain_net_gagnant': gain_net_gagnant,
    }
    return render(request, 'tontine/detail_groupe.html', context)


# --- LA FONCTION QUE TU NE VOYAIS PAS ---
@login_required
def creer_groupe(request):
    if request.method == "POST":
        nom = request.POST.get('nom_groupe')
        montant = request.POST.get('montant_cotisation')
        # Création du groupe
        groupe = TontineGroup.objects.create(
            name=nom,
            contribution_amount=montant,
            admin_groupe=request.user
        )
        # L'admin est vérifié d'office car il crée le groupe
        Membership.objects.create(user=request.user, group=groupe, is_verified=True)
        return redirect('tableau_bord_admin')
    return render(request, 'tontine/creer_groupe.html')


# 8. TIRAGE ET ACTIONS
@login_required
def effectuer_tirage(request, groupe_id):
    groupe = get_object_or_404(TontineGroup, id=groupe_id, admin_groupe=request.user)
    # On ne tire au sort que parmi ceux qui ont réellement payé dans l'appli
    membres_eligibles = Membership.objects.filter(group=groupe, is_verified=True)

    if membres_eligibles.exists():
        membres_eligibles.update(a_approuve_session=False)
        gagnant_membership = random.choice(membres_eligibles)
        groupe.dernier_gagnant = gagnant_membership.user

        # --- MODIFICATION ICI ---
        # On ne force plus la valeur ici.
        # C'est la vue 'detail_groupe' qui affichera le montant réel au rafraîchissement.

        groupe.en_attente_de_deblocage = True
        groupe.nombre_approbations = 0
        groupe.save()
        messages.success(request, f"Tirage effectué pour {groupe.dernier_gagnant.username} !")
    else:
        messages.error(request, "Impossible de tirer : personne n'a encore payé !")

    return redirect('detail_groupe', groupe_id=groupe.id)


@login_required
def approuver_transfert(request, groupe_id):
    groupe = get_object_or_404(TontineGroup, id=groupe_id)
    membership = get_object_or_404(Membership, user=request.user, group=groupe)

    if request.user == groupe.dernier_gagnant:
        messages.error(request, "Vous ne pouvez pas voter pour vous-même !")
        return redirect('mon_espace')

    if not membership.a_approuve_session:
        membership.a_approuve_session = True
        membership.save()
        messages.success(request, "Approbation enregistrée !")

    total_requis = groupe.membres.count() - 1
    groupe.nombre_approbations = Membership.objects.filter(group=groupe, a_approuve_session=True).count()

    if groupe.nombre_approbations >= total_requis:
        groupe.en_attente_de_deblocage = False
        messages.success(request, "🔒 Argent débloqué !")

    groupe.save()
    return redirect('mon_espace')


@login_required
def mettre_a_jour_lien_whatsapp(request, groupe_id):
    groupe = get_object_or_404(TontineGroup, id=groupe_id, admin_groupe=request.user)
    if request.method == "POST":
        lien = request.POST.get('whatsapp_link')
        groupe.whatsapp_group_link = lien
        groupe.save()
        messages.success(request, "Lien WhatsApp mis à jour !")
    return redirect('detail_groupe', groupe_id=groupe.id)


@login_required
def supprimer_groupe(request, groupe_id):
    groupe = get_object_or_404(TontineGroup, id=groupe_id, admin_groupe=request.user)
    groupe.delete()
    return redirect('tableau_bord_admin')


def contact(request):
    return render(request, 'tontine/contact.html')


def aide(request):
    return render(request, 'tontine/aide.html')

def designer_gagnant_manuel(request, groupe_id, user_id):
    # Sécurité : Seul l'admin du groupe peut faire ça
    groupe = get_object_or_404(TontineGroup, id=groupe_id, admin_groupe=request.user)
    gagnant = get_object_or_404(User, id=user_id)

    # 1. Calcul du montant de la caisse
    membres_payes = Membership.objects.filter(group=groupe, is_verified=True).count()
    montant_total = membres_payes * groupe.contribution_amount

    # 2. Mise à jour du groupe et RÉINITIALISATION DES VOTES
    groupe.dernier_gagnant = gagnant
    groupe.en_attente_de_deblocage = True # L'argent est bloqué jusqu'au vote
    groupe.nombre_approbations = 0 # On remet les votes à zéro pour le nouveau gagnant
    groupe.save()

    # On remet aussi à False le statut de vote de chaque membre
    Membership.objects.filter(group=groupe).update(a_approuve_session=False)

    # 3. Création de l'historique
    HistoriqueGagnant.objects.create(
        groupe=groupe,
        gagnant=gagnant,
        montant_gagne=montant_total
    )

    messages.success(request, f"Historique mis à jour pour {gagnant.username} !")
    return redirect('detail_groupe', groupe_id=groupe.id)

@login_required
def voir_historique(request):
    # On récupère tous les gains, du plus récent au plus ancien
    historique = HistoriqueGagnant.objects.all().order_by('-date_choix')
    return render(request, 'tontine/historique_gains.html', {'historique': historique})


@login_required
def effectuer_cotisation(request, group_id):
    groupe = get_object_or_404(TontineGroup, id=group_id)
    # On récupère le montant total incluant les frais de 3%
    montant_total = groupe.total_deposit_amount

    if request.method == "POST":
        reference = request.POST.get('reference')
        # Création de la transaction en attente de vérification API ou Admin
        membership = get_object_or_404(Membership, user=request.user, group=groupe)
        Transaction.objects.create(
            membership=membership,
            amount=montant_total,
            reference_api=reference
        )
        messages.success(request, "Référence envoyée ! Un admin validera votre paiement sous peu.")
        return redirect('mon_espace')

    return render(request, 'tontine/payer_mobile.html', {
        'groupe': groupe,
        'montant_total': montant_total
    })


@login_required
def demander_retrait(request, groupe_id):
    groupe = get_object_or_404(TontineGroup, id=groupe_id)

    # Sécurité : seul le dernier gagnant peut cliquer
    if request.user != groupe.dernier_gagnant:
        messages.error(request, "Vous n'êtes pas le gagnant actuel.")
        return redirect('mon_espace')

    groupe.en_attente_de_deblocage = True
    groupe.save()

    messages.info(request, "Demande de retrait lancée. Les autres membres doivent maintenant approuver.")
    return redirect('mon_espace')


@csrf_exempt  # Obligatoire car Campay n'envoie pas de jeton CSRF
def campay_webhook(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        # Campay envoie généralement le statut et la référence
        status = data.get('status')
        reference_externe = data.get('reference')  # L'ID de transaction Campay

        if status == 'SUCCESSFUL':
            # On cherche la transaction correspondante dans notre base
            try:
                transaction = Transaction.objects.get(reference_api=reference_externe)
                transaction.is_confirmed = True
                transaction.save()

                # On valide aussi l'adhésion du membre automatiquement !
                membership = transaction.membership
                membership.is_verified = True
                membership.save()

                return HttpResponse(status=200)
            except Transaction.DoesNotExist:
                return HttpResponse(status=404)

    return HttpResponse(status=400)


@login_required
def initier_paiement_campay(request, group_id):
    groupe = get_object_or_404(TontineGroup, id=group_id)
    membership = get_object_or_404(Membership, user=request.user, group=groupe)

    if request.method == "POST":
        phone = request.POST.get('phone')
        amount = int(groupe.contribution_amount * Decimal('1.03'))

        # ÉTAPE A : Obtenir le jeton de session (Indispensable)
        auth_url = "https://demo.campay.net/api/token/"
        auth_data = {
            "username": settings.CAMPAY_USERNAME,
            "password": settings.CAMPAY_PASSWORD
        }

        try:
            auth_response = requests.post(auth_url, json=auth_data)
            token = auth_response.json().get('token')

            # ÉTAPE B : Lancer la collecte avec le nouveau jeton
            collect_url = "https://demo.campay.net/api/collect/"
            headers = {
                "Authorization": f"Token {token}",
                "Content-Type": "application/json"
            }
            payload = {
                "amount": str(amount),
                "currency": "XAF",
                "from": phone,
                "description": f"Cotisation - {groupe.name}",
                "external_reference": f"T-{membership.id}-{random.randint(1000, 9999)}"
            }

            response = requests.post(collect_url, json=payload, headers=headers)
            res_data = response.json()

            if response.status_code == 200:
                Transaction.objects.create(
                    membership=membership,
                    amount=amount,
                    reference_api=res_data.get('reference'),
                    is_confirmed=False
                )
                messages.success(request, "Vérifiez votre téléphone pour confirmer !")
            else:
                messages.error(request, f"Campay dit : {res_data.get('message', 'Échec')}")
        except Exception as e:
            messages.error(request, f"Erreur technique : {str(e)}")

        return redirect('mon_espace')

    return render(request, 'tontine/payer_mobile.html', {'groupe': groupe})