# --- Validation des canaux d'alerte -------------------------------------------------------

def test_un_canal_actif_sans_adresse_est_refuse():
    from secdailybrief import config

    assert config.canaux_invalides({"slack": True}, {"slack": ""}) == "vide"
    assert config.canaux_invalides({"telegram": True}, {"telegram": "  "}) == "vide"


def test_une_adresse_sans_https_est_refusee():
    from secdailybrief import config

    assert config.canaux_invalides({"slack": True},
                                   {"slack": "hooks.slack.com/services/x"}) == "url"
    # Une adresse en http reste acceptee : un webhook auto-heberge peut l'exiger.
    assert config.canaux_invalides({"discord": True},
                                   {"discord": "http://discord.com/api/webhooks/1"}) is None


def test_un_jeton_telegram_improbable_est_refuse():
    from secdailybrief import config

    assert config.canaux_invalides({"telegram": True},
                                   {"telegram": "abc"}) == "jeton"
    jeton = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
    assert config.canaux_invalides({"telegram": True},
                                   {"telegram": jeton, "telegram_chat": "-1001234567890"}) is None


def test_un_canal_inactif_n_est_pas_valide():
    """Une adresse vide dans un canal éteint n'est pas une faute."""
    from secdailybrief import config

    assert config.canaux_invalides({"slack": False}, {"slack": ""}) is None
    assert config.canaux_invalides({}, {}) is None

def test_un_identifiant_de_conversation_vide_est_refuse():
    """Le canal etait coche, muet, et rien ne le disait : runner exige les deux valeurs."""
    from secdailybrief import config

    jeton = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
    assert config.canaux_invalides({"telegram": True},
                                   {"telegram": jeton, "telegram_chat": "  "}) == "vide"


def test_un_identifiant_de_conversation_mal_forme_est_refuse():
    from secdailybrief import config

    jeton = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
    assert config.canaux_invalides({"telegram": True},
                                   {"telegram": jeton, "telegram_chat": "mon groupe"}) == "chat"


def test_les_formes_valides_d_identifiant_sont_acceptees():
    from secdailybrief import config

    jeton = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
    for chat in ("-1001234567890", "123456789", "@moncanal"):
        assert config.canaux_invalides({"telegram": True},
                                       {"telegram": jeton, "telegram_chat": chat}) is None
