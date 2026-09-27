from __future__ import annotations

LANGUAGES = (
    "ΑΛΒΑΝΙΚΑ",
    "ΑΓΓΛΙΚΑ",
    "ΓΑΛΛΙΚΑ",
    "ΙΤΑΛΙΚΑ",
    "ΣΕΡΒΙΚΑ",
    "ΒΟΡΕΙΑ ΜΑΚΕΔΟΝΙΑ",
)

# Only the second-language text is replaced. Greek text and all Word OOXML
# structure/layout stay untouched. Albanian returns an empty replacement map,
# therefore it remains the byte-for-byte behavioral baseline of the old flow.
TRANSLATIONS = {
    "REPUBLIKA GREKE": {
        "ΑΓΓΛΙΚΑ": "HELLENIC REPUBLIC",
        "ΓΑΛΛΙΚΑ": "RÉPUBLIQUE HELLÉNIQUE",
        "ΙΤΑΛΙΚΑ": "REPUBBLICA ELLENICA",
        "ΣΕΡΒΙΚΑ": "REPUBLIKA GRČKA",
        "ΒΟΡΕΙΑ ΜΑΚΕΔΟΝΙΑ": "РЕПУБЛИКА ГРЦИЈА",
    },
    "MINISTRIA E MBROJTJES SË QYTETARËVE": {
        "ΑΓΓΛΙΚΑ": "MINISTRY OF CITIZEN PROTECTION",
        "ΓΑΛΛΙΚΑ": "MINISTÈRE DE LA PROTECTION DU CITOYEN",
        "ΙΤΑΛΙΚΑ": "MINISTERO DELLA PROTEZIONE DEL CITTADINO",
        "ΣΕΡΒΙΚΑ": "MINISTARSTVO ZA ZAŠTITU GRAĐANA",
        "ΒΟΡΕΙΑ ΜΑΚΕΔΟΝΙΑ": "МИНИСТЕРСТВО ЗА ЗАШТИТА НА ГРАЃАНИТЕ",
    },
    "SHTABI I POLICISË GREKE": {
        "ΑΓΓΛΙΚΑ": "HELLENIC POLICE HEADQUARTERS",
        "ΓΑΛΛΙΚΑ": "QUARTIER GÉNÉRAL DE LA POLICE HELLÉNIQUE",
        "ΙΤΑΛΙΚΑ": "QUARTIER GENERALE DELLA POLIZIA ELLENICA",
        "ΣΕΡΒΙΚΑ": "GLAVNI ŠTAB GRČKE POLICIJE",
        "ΒΟΡΕΙΑ ΜΑΚΕΔΟΝΙΑ": "ГЛАВЕН ШТАБ НА ГРЧКАТА ПОЛИЦИЈА",
    },
    "DEPARTAMENTI I POLICISË FLORINË": {
        "ΑΓΓΛΙΚΑ": "FLORINA POLICE DIRECTORATE",
        "ΓΑΛΛΙΚΑ": "DIRECTION DE LA POLICE DE FLORINA",
        "ΙΤΑΛΙΚΑ": "DIREZIONE DI POLIZIA DI FLORINA",
        "ΣΕΡΒΙΚΑ": "POLICIJSKA UPRAVA FLORINA",
        "ΒΟΡΕΙΑ ΜΑΚΕΔΟΝΙΑ": "ПОЛИЦИСКА УПРАВА ФЛОРИНА",
    },
    "DEPARTAMENTI I KONTROLLIT TË PASAPORTËVE KRΥSTALLOPIGI": {
        "ΑΓΓΛΙΚΑ": "KRYSTALLOPIGI PASSPORT CONTROL DEPARTMENT",
        "ΓΑΛΛΙΚΑ": "SERVICE DE CONTRÔLE DES PASSEPORTS DE KRYSTALLOPIGI",
        "ΙΤΑΛΙΚΑ": "UFFICIO CONTROLLO PASSAPORTI DI KRYSTALLOPIGI",
        "ΣΕΡΒΙΚΑ": "ODELJENJE PASOŠKE KONTROLE KRYSTALLOPIGI",
        "ΒΟΡΕΙΑ ΜΑΚΕΔΟΝΙΑ": "ОДДЕЛЕНИЕ ЗА ПАСОШКА КОНТРОЛА КРИСТАЛОПИГИ",
    },
    "NUMRI I PROTOKOLLIT": {
        "ΑΓΓΛΙΚΑ": "PROTOCOL No.",
        "ΓΑΛΛΙΚΑ": "N° DE PROTOCOLE",
        "ΙΤΑΛΙΚΑ": "N. DI PROTOCOLLO",
        "ΣΕΡΒΙΚΑ": "BROJ PROTOKOLA",
        "ΒΟΡΕΙΑ ΜΑΚΕΔΟΝΙΑ": "БРОЈ НА ПРОТОКОЛ",
    },
    "REFUZIMI I HYRJES NË KUFI": {
        "ΑΓΓΛΙΚΑ": "REFUSAL OF ENTRY AT THE BORDER",
        "ΓΑΛΛΙΚΑ": "REFUS D’ENTRÉE À LA FRONTIÈRE",
        "ΙΤΑΛΙΚΑ": "RESPINGIMENTO ALLA FRONTIERA",
        "ΣΕΡΒΙΚΑ": "ODBIJANJE ULASKA NA GRANICI",
        "ΒΟΡΕΙΑ ΜΑΚΕΔΟΝΙΑ": "ОДБИВАЊЕ ВЛЕЗ НА ГРАНИЦА",
    },
    "data": {"ΑΓΓΛΙΚΑ":"date","ΓΑΛΛΙΚΑ":"date","ΙΤΑΛΙΚΑ":"data","ΣΕΡΒΙΚΑ":"datum","ΒΟΡΕΙΑ ΜΑΚΕΔОНИЈА":"датум"},
    "ora": {"ΑΓΓΛΙΚΑ":"time","ΓΑΛΛΙΚΑ":"heure","ΙΤΑΛΙΚΑ":"ora","ΣΕΡΒΙΚΑ":"vreme","ΒΟΡΕΙΑ ΜΑΚΕДОНИЈА":"време"},
    "nepikenkufitareteKalimit": {"ΑΓΓΛΙΚΑ":"at the border crossing point","ΓΑΛΛΙΚΑ":"au point de passage frontalier","ΙΤΑΛΙΚΑ":"al valico di frontiera","ΣΕΡΒΙΚΑ":"na graničnom prelazu","ΒΟΡЕΙΑ МΑΚЕДОНИЈА":"на граничниот премин"},
    "Autoriteti i poshteshenuar ka perpara tij": {"ΑΓΓΛΙΚΑ":"the undersigned authority has before it","ΓΑΛΛΙΚΑ":"l’autorité soussignée a devant elle","ΙΤΑΛΙΚΑ":"l’autorità sottoscritta ha dinanzi a sé","ΣΕΡΒΙΚΑ":"dole potpisani organ ima pred sobom","ΒΟΡΕΙΑ МΑΚЕДОНИЈА":"долупотпишаниот орган го има пред себе"},
    "Mbiemri": {"ΑΓΓΛΙΚΑ":"Surname","ΓΑΛΛΙΚΑ":"Nom","ΙΤΑΛΙΚΑ":"Cognome","ΣΕΡΒΙΚΑ":"Prezime","ΒΟΡΕΙΑ МΑΚЕДОНИЈА":"Презиме"},
    "Emri": {"ΑΓΓΛΙΚΑ":"Name","ΓΑΛΛΙΚΑ":"Prénom","ΙΤΑΛΙΚΑ":"Nome","ΣΕΡΒΙΚΑ":"Ime","ΒΟΡΕΙΑ ΜΑΚΕДОНИЈΑ":"Име"},
    "Dataelindjes": {"ΑΓΓΛΙΚΑ":"Date of birth","ΓΑΛΛΙΚΑ":"Date de naissance","ΙΤΑΛΙΚΑ":"Data di nascita","ΣΕΡΒΙΚΑ":"Datum rođenja","ΒΟΡЕΙΑ ΜΑΚΕДОНИЈΑ":"Датум на раѓање"},
    "vendiilindjes": {"ΑΓΓΛΙΚΑ":"place of birth","ΓΑΛΛΙΚΑ":"lieu de naissance","ΙΤΑΛΙΚΑ":"luogo di nascita","ΣΕΡΒΙΚΑ":"mesto rođenja","ΒΟΡΕΙΑ ΜΑΚΕДОНИЈА":"место на раѓање"},
    "seksi": {"ΑΓΓΛΙΚΑ":"sex","ΓΑΛΛΙΚΑ":"sexe","ΙΤΑΛΙΚΑ":"sesso","ΣΕΡΒΙΚΑ":"pol","ΒΟΡΕΙΑ ΜΑΚΕДОНИЈΑ":"пол"},
    "shtetësia": {"ΑΓΓΛΙΚΑ":"nationality","ΓΑΛΛΙΚΑ":"nationalité","ΙΤΑΛΙΚΑ":"cittadinanza","ΣΕΡΒΙΚΑ":"državljanstvo","ΒΟΡΕΙΑ ΜΑΚΕДОНИЈΑ":"државјанство"},
    "banor": {"ΑΓΓΛΙΚΑ":"resident","ΓΑΛΛΙΚΑ":"résident","ΙΤΑΛΙΚΑ":"residente","ΣΕΡΒΙΚΑ":"prebivalište","ΒΟΡΕΙΑ ΜΑΚΕДОНИЈА":"живеалиште"},
    "Mbajtësiikartëssë identitetit/pasaportës": {"ΑΓΓΛΙΚΑ":"Holder of identity card/passport","ΓΑΛΛΙΚΑ":"Titulaire de la carte d’identité/du passeport","ΙΤΑΛΙΚΑ":"Titolare della carta d’identità/passaporto","ΣΕΡΒΙΚΑ":"Nosilac lične karte/pasoša","ΒΟΡΕΙΑ ΜΑΚЕДОНИЈА":"Носител на лична карта/пасош"},
    "numri": {"ΑΓΓΛΙΚΑ":"number","ΓΑΛΛΙΚΑ":"numéro","ΙΤΑΛΙΚΑ":"numero","ΣΕΡΒΙΚΑ":"broj","ΒΟΡΕΙΑ ΜΑΚΕДОНИЈΑ":"број"},
    "Autoritetilëshues": {"ΑΓΓΛΙΚΑ":"Issuing authority","ΓΑΛΛΙΚΑ":"Autorité de délivrance","ΙΤΑΛΙΚΑ":"Autorità di rilascio","ΣΕΡΒΙΚΑ":"Organ izdavanja","ΒΟΡΕΙΑ ΜΑΚЕДОНИЈА":"Орган на издавање"},
    "datat e lëshimit": {"ΑΓΓΛΙΚΑ":"date of issue","ΓΑΛΛΙΚΑ":"date de délivrance","ΙΤΑΛΙΚΑ":"data di rilascio","ΣΕΡΒΙΚΑ":"datum izdavanja","ΒΟΡΕΙΑ ΜΑΚΕДОНИЈΑ":"датум на издавање"},
    "Mbajtësi i vizësnr": {"ΑΓΓΛΙΚΑ":"Holder of visa No.","ΓΑΛΛΙΚΑ":"Titulaire du visa n°","ΙΤΑΛΙΚΑ":"Titolare del visto n.","ΣΕΡΒΙΚΑ":"Nosilac vize br.","ΒΟΡΕΙΑ МΑΚΕДОНИЈΑ":"Носител на виза бр."},
    "lloji": {"ΑΓΓΛΙΚΑ":"type","ΓΑΛΛΙΚΑ":"type","ΙΤΑΛΙΚΑ":"tipo","ΣΕΡΒΙΚΑ":"vrsta","ΒΟΡΕΙΑ МΑΚЕДОНИЈΑ":"вид"},
    "e cilaështëdhënënga": {"ΑΓΓΛΙΚΑ":"issued by","ΓΑΛΛΙΚΑ":"délivré par","ΙΤΑΛΙΚΑ":"rilasciato da","ΣΕΡΒΙΚΑ":"izdata od","ΒΟΡЕΙΑ МΑΚЕДОНИЈΑ":"издадена од"},
    "e vlefshmenga": {"ΑΓΓΛΙΚΑ":"valid from","ΓΑΛΛΙΚΑ":"valable du","ΙΤΑΛΙΚΑ":"valido dal","ΣΕΡΒΙΚΑ":"važi od","ΒΟΡЕΙΑ МΑΚЕДОНИЈА":"важи од"},
    "deri sa": {"ΑΓΓΛΙΚΑ":"until","ΓΑΛΛΙΚΑ":"jusqu’au","ΙΤΑΛΙΚΑ":"fino al","ΣΕΡΒΙΚΑ":"do","ΒΟΡΕΙΑ МΑΚΕДОНИЈΑ":"до"},
    "për një periudhë kohe": {"ΑΓΓΛΙΚΑ":"for a period of","ΓΑΛΛΙΚΑ":"pour une durée de","ΙΤΑΛΙΚΑ":"per un periodo di","ΣΕΡΒΙΚΑ":"za period od","ΒΟΡΕΙΑ МΑΚΕДОНИЈА":"за период од"},
    "ditë, per aresyet emeposhtme": {"ΑΓΓΛΙΚΑ":"days, for the following reasons","ΓΑΛΛΙΚΑ":"jours, pour les motifs suivants","ΙΤΑΛΙΚΑ":"giorni, per i seguenti motivi","ΣΕΡΒΙΚΑ":"dana, iz sledećih razloga","ΒΟΡΕΙΑ МΑΚЕДОНИЈА":"дена, од следните причини"},
    "meorigjinënga": {"ΑΓΓΛΙΚΑ":"coming from","ΓΑΛΛΙΚΑ":"en provenance de","ΙΤΑΛΙΚΑ":"proveniente da","ΣΕΡΒΙΚΑ":"dolazi iz","ΒΟΡΕΙΑ МΑΚЕДОНИЈΑ":"доаѓа од"},
    "merrugë": {"ΑΓΓΛΙΚΑ":"by road","ΓΑΛΛΙΚΑ":"par voie routière","ΙΤΑΛΙΚΑ":"via strada","ΣΕΡΒΙΚΑ":"drumskim putem","ΒΟΡΕΙΑ МΑΚЕДОНИЈА":"по копнен пат"},
    "i cili është informuar se për personin e tij është marrë vendim për ndalimin e hyrjes në vend": {"ΑΓΓΛΙΚΑ":"who has been informed that a decision refusing entry into the country has been taken in respect of him/her","ΓΑΛΛΙΚΑ":"qui a été informé(e) qu’une décision de refus d’entrée dans le pays a été prise à son encontre","ΙΤΑΛΙΚΑ":"che è stato/a informato/a che nei suoi confronti è stata adottata una decisione di respingimento","ΣΕΡΒΙΚΑ":"koji/a je obavešten/a da je u odnosu na njega/nju doneta odluka o odbijanju ulaska u zemlju","ΒΟΡΕΙΑ МΑΚЕДОНИЈА":"кој/а е известен/а дека за него/неа е донесена одлука за одбивање влез во земјата"},
    "ne baze": {"ΑΓΓΛΙΚΑ":"pursuant to","ΓΑΛΛΙΚΑ":"en vertu de","ΙΤΑΛΙΚΑ":"ai sensi di","ΣΕΡΒΙΚΑ":"na osnovu","ΒΟΡΕΙΑ МΑΚЕДОНИЈА":"врз основа на"},
    "per aresyet e meposhtme": {"ΑΓΓΛΙΚΑ":"for the following reasons","ΓΑΛΛΙΚΑ":"pour les motifs suivants","ΙΤΑΛΙΚΑ":"per i seguenti motivi","ΣΕΡΒΙΚΑ":"iz sledećih razloga","ΒΟΡΕΙΑ МΑΚЕДОНИЈА":"од следните причини"},
    "Nuk disponon dokument/-e te vlefshem/-me udhetimi.": {"ΑΓΓΛΙΚΑ":"Does not possess valid travel document(s).","ΓΑΛΛΙΚΑ":"Ne possède pas de document(s) de voyage valable(s).","ΙΤΑΛΙΚΑ":"Non è in possesso di documento/i di viaggio valido/i.","ΣΕΡΒΙΚΑ":"Ne poseduje važeću putnu ispravu / važeće putne isprave.","ΒΟΡΕΙΑ МΑΚΕДОНИЈΑ":"Не поседува важечка патна исправа / важечки патни исправи."},
    "Paraqitidokurneniudhetimifals, tefalsifikuarosetemanipuluar.": {"ΑΓΓΛΙΚΑ":"Presented false, counterfeit or altered travel document(s).","ΓΑΛΛΙΚΑ":"A présenté un ou plusieurs documents de voyage faux, contrefaits ou falsifiés.","ΙΤΑΛΙΚΑ":"Ha presentato documento/i di viaggio falso/i, contraffatto/i o alterato/i.","ΣΕΡΒΙΚΑ":"Predočio/la je lažnu, falsifikovanu ili preinačenu putnu ispravu.","ΒΟΡΕΙΑ МΑΚЕДОНИЈА":"Приложи лажна, фалсификувана или преправена патна исправа."},
    "Nukdispononvizetevlefshmeoselejeqendrimi.": {"ΑΓΓΛΙΚΑ":"Does not possess a valid visa or residence permit.","ΓΑΛΛΙΚΑ":"Ne possède pas de visa ou de titre de séjour valable.","ΙΤΑΛΙΚΑ":"Non è in possesso di un visto o permesso di soggiorno valido.","ΣΕΡΒΙΚΑ":"Ne poseduje važeću vizu ili dozvolu boravka.","ΒΟΡΕΙΑ МΑΚЕДОНИЈΑ":"Не поседува важечка виза или дозвола за престој."},
    "Paraqitivizeoselejeqendrimi false, tefalsifikuarosetemanipuluar.": {"ΑΓΓΛΙΚΑ":"Presented a false, counterfeit or altered visa or residence permit.","ΓΑΛΛΙΚΑ":"A présenté un visa ou un titre de séjour faux, contrefait ou falsifié.","ΙΤΑΛΙΚΑ":"Ha presentato un visto o permesso di soggiorno falso, contraffatto o alterato.","ΣΕΡΒΙΚΑ":"Predočio/la je lažnu, falsifikovanu ili preinačenu vizu ili dozvolu boravka.","ΒΟΡΕΙΑ МΑΚΕДОНИЈΑ":"Приложи лажна, фалсификувана или преправена виза или дозвола за престој."},
    "Ai tashmë ka qëndruar për 90 ditë brenda një periudhe 180 ditore në territorin e shteteve anëtare të Bashkimit Evropian.": {"ΑΓΓΛΙΚΑ":"Has already stayed for 90 days during the current 180-day period in the territory of the Member States of the European Union.","ΓΑΛΛΙΚΑ":"A déjà séjourné 90 jours au cours de la période actuelle de 180 jours sur le territoire des États membres de l’Union européenne.","ΙΤΑΛΙΚΑ":"Ha già soggiornato per 90 giorni nell’attuale periodo di 180 giorni nel territorio degli Stati membri dell’Unione europea.","ΣΕΡΒΙΚΑ":"Već je boravio/la 90 dana tokom tekućeg perioda od 180 dana na teritoriji država članica Evropske unije.","ΒΟΡΕΙΑ МΑΚΕДОНИЈΑ":"Веќе престојувал/а 90 дена во тековниот период од 180 дена на територијата на земјите членки на Европската Унија."},
    "I interesuari": {"ΑΓΓΛΙΚΑ":"Person concerned","ΓΑΛΛΙΚΑ":"Personne concernée","ΙΤΑΛΙΚΑ":"Interessato","ΣΕΡΒΙΚΑ":"Zainteresovano lice","ΒΟΡΕΙΑ МΑΚЕДОНИЈА":"Засегнатото лице"},
    "Nepunesi kopetent per kontrollin": {"ΑΓΓΛΙΚΑ":"Officer responsible for the check","ΓΑΛΛΙΚΑ":"Agent chargé du contrôle","ΙΤΑΛΙΚΑ":"Agente responsabile del controllo","ΣΕΡΒΙΚΑ":"Službenik nadležan za kontrolu","ΒΟΡΕΙΑ МΑΚЕДОНИЈΑ":"Службеник надлежен за контролата"},
}

def replacements(language: str) -> dict[str, str]:
    lang = (language or "ΑΛΒΑΝΙΚΑ").strip().upper()
    if lang == "ΑΛΒΑΝΙΚΑ":
        return {}
    if lang not in LANGUAGES:
        raise ValueError(f"Μη υποστηριζόμενη γλώσσα άρνησης: {language}")
    return {source: values[lang] for source, values in TRANSLATIONS.items() if lang in values}
