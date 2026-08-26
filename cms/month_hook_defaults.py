# cms/month_hook_defaults.py — default “Känner du igen” copy for seed_site

"""Default MonthHook rows. Live edits: Admin → CMS → Känner du igen."""

# Adjust: only used when seeding empty/missing months — admin edits win after that
# if seed uses update_or_create (it overwrites). Prefer update_or_create for deploy
# parity with SeasonTip tips.
MONTH_HOOK_DEFAULTS = {
    1: {
        "icon": "❄️",
        "quote": "Mina fötter känns torra och trötta och jag vill bara få dem omhändertagna.",
        "body": "Låt någon annan ta hand om dem en stund.",
        "cta": "Fotvård med mjukgörande vård och massage",
    },
    2: {
        "icon": "❤️",
        "quote": "Jag vill kunna hålla fram händerna utan att tänka på nagelbanden.",
        "body": "Välvårdade naglar och nagelband gör mycket för känslan av händerna.",
        "cta": "Manikyr & nagelvård",
    },
    3: {
        "icon": "🌱",
        "quote": "Mina skor känns inte riktigt som de brukar.",
        "body": (
            "När du börjar gå mer kan det vara skönt att se om ett skoinlägg "
            "passar just dina skor och fötter."
        ),
        "cta": "Kom och prova skoinlägg",
    },
    4: {
        "icon": "🌷",
        "quote": "Varför ser mina naglar så ojämna ut?",
        "body": (
            "Naglar som skivar sig, går av eller känns tunna behöver inte bara "
            "döljas med lack. Vi kan ge dem omsorg och vårda dem ordentligt."
        ),
        "cta": "Manikyr & nagelvård",
    },
    5: {
        "icon": "🌸",
        "quote": "Jag vill gärna ha fina fötter när sandalerna åker fram.",
        "body": (
            "Fräscha naglar, välvårdad hud och en stunds fotvård innan fötterna "
            "kommer fram i ljuset."
        ),
        "cta": "Fotvård & tånagellack",
    },
    6: {
        "icon": "☀️",
        "quote": "Mina fötter har varit med på mycket – nu behöver de en paus.",
        "body": (
            "Efter promenader, bad och barfotadagar kan en stunds behandling "
            "vara precis det fötterna behöver."
        ),
        "cta": "Fotvård eller fotmassage",
    },
    7: {
        "icon": "🌞",
        "quote": "Jag har semester – men mina fötter har gått hela dagen.",
        "body": (
            "Shopping, strand, utflykter och långa promenader. "
            "Nu kan du låta någon annan ta hand om fötterna."
        ),
        "cta": "Fot- & vadmassage",
    },
    8: {
        "icon": "🌾",
        "quote": "Mina fötter känns inte direkt som semester längre…",
        "body": (
            "Ibland behövs det inte mer än en ordentlig genomgång, lite omsorg "
            "och en skön behandling."
        ),
        "cta": "Återhämtande fotvård",
    },
    9: {
        "icon": "🍂",
        "quote": "Nu ska jag plötsligt ha fötterna i skor hela dagarna igen.",
        "body": (
            "Känns skorna fortfarande bra? "
            "Kom och prova mina skoinlägg innan höstens promenader drar igång på riktigt."
        ),
        "cta": "Prova skoinlägg",
    },
    10: {
        "icon": "🍁",
        "quote": "Mina händer får göra allt – men när fick de själva lite omsorg?",
        "body": "Tvätta, arbeta, laga mat, städa, skriva… händerna arbetar hela dagen.",
        "cta": "Manikyr eller handmassage",
    },
    11: {
        "icon": "🌧️",
        "quote": "Jag fryser bara jag tittar på mina händer.",
        "body": "Kalla dagar passar perfekt för något varmt, mjukt och avkopplande.",
        "cta": "Värmande manikyr eller värmande fotvård",
    },
    12: {
        "icon": "🎄",
        "quote": "Alla andra är fixade – men jag då?",
        "body": (
            "Julens alla måsten kan vänta en liten stund. "
            "Sätt dig ner och låt någon annan ta hand om dina händer eller fötter."
        ),
        "cta": "Manikyr, fotvård eller massage",
    },
}
