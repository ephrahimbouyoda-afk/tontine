from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal  # IMPORTANT pour les calculs financiers

# 1. Le groupe avec les champs de sécurité
class TontineGroup(models.Model):
    name = models.CharField(max_length=255)
    contribution_amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency_days = models.IntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    admin_groupe = models.ForeignKey(User, on_delete=models.CASCADE, related_name='groupes_crees')
    whatsapp_group_link = models.URLField(max_length=500, blank=True, null=True)

    # --- LES MÉTHODES POUR LE CALCUL AUTOMATIQUE ---

    @property
    def total_deposit_amount(self):
        """Calcule ce que le membre doit payer sur son téléphone (Montant + 3%)"""
        # On utilise Decimal('0.03') pour la précision
        fees = self.contribution_amount * Decimal('0.03')
        return self.contribution_amount + fees

    @property
    def admin_commission_total(self):
        """Calcule ton gain sur la caisse totale (2% du pot commun)"""
        # Correction ici : on utilise 'membres' car c'est ton related_name
        total_pot = self.contribution_amount * self.membres.count()
        return total_pot * Decimal('0.02')

    @property
    def winner_net_gain(self):
        """Calcule ce que le gagnant reçoit réellement (Pot - Ta Commission)"""
        total_pot = self.contribution_amount * self.membres.count()
        return total_pot - self.admin_commission_total

    # CHAMPS POUR LE TIRAGE ET LA CAISSE
    caisse_totale = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dernier_gagnant = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="gains")

    # --- SÉCURITÉ MULTI-MEMBRES ---
    en_attente_de_deblocage = models.BooleanField(default=False)
    nombre_approbations = models.IntegerField(default=0)

    def __str__(self):
        return self.name

# 2. Le lien entre membre et groupe
class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(TontineGroup, on_delete=models.CASCADE, related_name='membres')
    is_verified = models.BooleanField(default=False)
    rank = models.IntegerField(null=True, blank=True)
    a_approuve_session = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} dans {self.group.name}"


# 3. Les transactions financières
class Transaction(models.Model):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    reference_api = models.CharField(max_length=100, unique=True)
    is_confirmed = models.BooleanField(default=False)

    # J'AI SUPPRIMÉ LA LIGNE QUI ÉTAIT ICI (L'ERREUR)

    def __str__(self):
        return f"Pay de {self.membership.user.username}"


# 4. L'HISTORIQUE DES GAGNANTS (Bien séparé et aligné à gauche)
class HistoriqueGagnant(models.Model):
    groupe = models.ForeignKey(TontineGroup, on_delete=models.CASCADE)
    gagnant = models.ForeignKey(User, on_delete=models.CASCADE)
    montant_gagne = models.DecimalField(max_digits=10, decimal_places=2)
    date_choix = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.gagnant.username} - {self.groupe.name} - {self.date_choix}"