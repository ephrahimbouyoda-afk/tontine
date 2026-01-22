from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- ACCUEIL ET AUTHENTIFICATION ---
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    # --- ESPACES UTILISATEURS ---
    path('mon-espace/', views.mon_espace, name='mon_espace'),
    path('admin-dashboard/', views.tableau_bord_admin, name='tableau_bord_admin'),

    # --- GESTION DES GROUPES ---
    path('creer-groupe/', views.creer_groupe, name='creer_groupe'),
    path('groupe/<int:groupe_id>/', views.detail_groupe, name='detail_groupe'),
    path('rejoindre/<int:groupe_id>/', views.rejoindre_via_lien, name='rejoindre_via_lien'),
    path('supprimer-groupe/<int:groupe_id>/', views.supprimer_groupe, name='supprimer_groupe'),
    path('groupe/<int:groupe_id>/update-whatsapp/', views.mettre_a_jour_lien_whatsapp, name='update_whatsapp'),

    # --- PAIEMENTS AUTOMATISÉS (CAMPAY) ---
    # C'est cette route que ton bouton "Payer" dans le HTML doit utiliser
    path('initier-paiement/<int:group_id>/', views.initier_paiement_campay, name='initier_paiement_campay'),
    # C'est l'URL que tu as donnée à Campay pour les confirmations
    path('campay-webhook/', views.campay_webhook, name='campay_webhook'),

    # --- ACTIONS DE TONTINE (TIRAGE, VOTES, RETRAITS) ---
    path('tirage/<int:groupe_id>/', views.effectuer_tirage, name='effectuer_tirage'),
    path('approuver-transfert/<int:groupe_id>/', views.approuver_transfert, name='approuver_transfert'),
    path('demander-retrait/<int:groupe_id>/', views.demander_retrait, name='demander_retrait'),
    path('groupe/<int:groupe_id>/designer-gagnant/<int:user_id>/', views.designer_gagnant_manuel, name='designer_gagnant_manuel'),
    path('historique-des-gains/', views.voir_historique, name='voir_historique'),

    # --- PAGES D'INFORMATION ---
    path('contact/', views.contact, name='contact'),
    path('aide/', views.aide, name='aide'),
]