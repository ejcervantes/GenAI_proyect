"""
Curated seed corpus — Pakistan → Germany visa guidance.

This is the trusted baseline the RAG is built on. Every entry carries the real
official source URL in ``source``; the live scraper (scraper.py) re-fetches that
URL daily and, when the fetched text differs from the stored snapshot, the RAG is
re-ingested. When a live fetch fails or returns thin content, this seed text is
used as the fallback so citations always point at a real official source.

Scope is deliberately narrow (Pakistani passport holders travelling to Germany)
so retrieval quality stays high for the primary user. Content is accurate to
public official guidance but MUST be verified against the source before relying
on it — figures (fees, blocked-account amounts) change frequently.

Fields per entry: source, passport_nationality, destination_country,
travel_purpose, title, content, last_scraped.
"""

MOCK_VISA_POLICIES: list[dict] = [
    # ── Student visa (National Visa / Type D) ────────────────────────────────
    {
        "source": "https://pakistan.diplo.de/pk-en/service/visa",
        "passport_nationality": "Pakistani",
        "destination_country": "Germany",
        "travel_purpose": "student",
        "title": "Germany Student Visa (National Visa, Type D) — Pakistani Citizens",
        "content": (
            "Pakistani citizens require a National Visa (Type D) to study in Germany for "
            "programmes longer than 90 days. Applications are submitted to the German Mission "
            "in Pakistan (Embassy Islamabad or Consulate General Karachi) by online appointment. "
            "Unlike India, China and Vietnam, Pakistan is NOT subject to the APS certificate "
            "requirement. Core documents: university admission letter (Zulassungsbescheid) or "
            "conditional admission, proof of financial means — typically a blocked account "
            "(Sperrkonto) of about €11,904 per year (verify the current amount, it is updated "
            "regularly) or a recognised scholarship, valid passport, biometric photos, German or "
            "English language proficiency as required by the programme, health insurance valid for "
            "the first weeks until enrolment, and the completed national visa application form. "
            "Processing time is typically 6 to 12 weeks, so apply as early as possible. After "
            "arrival in Germany students must register their address and apply for a residence "
            "permit for study purposes."
        ),
        "last_scraped": "2025-01-01",
    },

    # ── Work / skilled migration ─────────────────────────────────────────────
    {
        "source": "https://www.make-it-in-germany.com/en/visa-residence/types",
        "passport_nationality": "Pakistani",
        "destination_country": "Germany",
        "travel_purpose": "work",
        "title": "Germany Work Visa & EU Blue Card — Pakistani Skilled Workers",
        "content": (
            "Pakistani nationals with a recognised qualification and a concrete job offer can apply "
            "for a German work visa under the Skilled Immigration Act "
            "(Fachkräfteeinwanderungsgesetz). Common routes: the EU Blue Card for university "
            "graduates meeting a minimum gross salary threshold, the general skilled-worker visa for "
            "recognised vocational qualifications, and — since June 2024 — the Opportunity Card "
            "(Chancenkarte), a points-based permit that allows entry to look for a job. Typical "
            "documents: valid passport, job contract or binding offer, recognised qualification "
            "(degree listed in the anabin database or a statement of comparability), CV, biometric "
            "photos, and proof of health insurance. Recognition of the foreign qualification is a "
            "key step and can add weeks to the timeline. Applications go through the German Mission "
            "in Pakistan; processing commonly takes 1 to 3 months including recognition."
        ),
        "last_scraped": "2025-01-01",
    },

    # ── Tourist / Schengen (Type C) ──────────────────────────────────────────
    {
        "source": "https://www.auswaertiges-amt.de/en/visa-service",
        "passport_nationality": "Pakistani",
        "destination_country": "Germany",
        "travel_purpose": "tourist",
        "title": "Germany Tourist / Schengen Visa (Type C) — Pakistani Citizens",
        "content": (
            "Pakistani passport holders require a Schengen Visa (Type C) for short visits to Germany "
            "of up to 90 days within any 180-day period for tourism, visiting family or business. "
            "Applications are lodged at the German Mission or its authorised visa application centre "
            "in Pakistan. Required documents: passport valid at least three months beyond the "
            "intended departure with at least two blank pages, completed Schengen application form, "
            "recent biometric photo, travel medical insurance with minimum €30,000 coverage, "
            "confirmed accommodation (hotel booking or formal invitation), round-trip flight "
            "reservation, recent bank statements (last three to six months) proving sufficient "
            "funds, and proof of employment, business or study ties to Pakistan. The standard "
            "Schengen visa fee is €90 for adults (verify the current fee). Decisions normally take "
            "about 15 calendar days but can extend to 45 days in individual cases."
        ),
        "last_scraped": "2025-01-01",
    },

    # ── Family reunion ───────────────────────────────────────────────────────
    {
        "source": "https://pakistan.diplo.de/pk-en/service/visa",
        "passport_nationality": "Pakistani",
        "destination_country": "Germany",
        "travel_purpose": "family",
        "title": "Germany Family Reunion Visa — Pakistani Citizens",
        "content": (
            "Pakistani nationals joining a spouse or close family member living in Germany apply for "
            "a National Visa (Type D) for family reunification at the German Mission in Pakistan. "
            "For spouse reunification, applicants generally must prove basic German language ability "
            "at level A1 with a certificate from a recognised institute such as the Goethe-Institut, "
            "with limited exemptions. Typical documents: valid passport, marriage certificate "
            "(attested and translated), the sponsor's residence permit or passport, proof of "
            "adequate living space and secured livelihood in Germany, health insurance, biometric "
            "photos, and the completed application form. Documents issued in Pakistan usually need "
            "attestation and certified German translation. Processing times vary widely and can "
            "take several months."
        ),
        "last_scraped": "2025-01-01",
    },

    # ── After arrival: registration & residence permit ───────────────────────
    {
        "source": "https://www.make-it-in-germany.com/en/living-in-germany/settling-in/registration",
        "passport_nationality": "Pakistani",
        "destination_country": "Germany",
        "travel_purpose": "general",
        "title": "After Arrival in Germany — Address Registration & Residence Permit",
        "content": (
            "After entering Germany on a National Visa, holders must complete two key steps. First, "
            "register the home address (Anmeldung) at the local residents' office (Bürgeramt or "
            "Einwohnermeldeamt), generally within about two weeks of moving in; this produces the "
            "registration certificate (Meldebescheinigung) needed for almost everything else, "
            "including opening a bank account. Second, before the entry visa expires, apply for the "
            "residence permit (Aufenthaltstitel) at the local Foreigners' Office (Ausländerbehörde) "
            "for the relevant purpose — study, work or family. Bring the passport with visa, "
            "registration certificate, biometric photos, proof of health insurance, proof of "
            "purpose (enrolment certificate, employment contract, etc.) and proof of financial "
            "means. Booking an Ausländerbehörde appointment early is strongly advised as waiting "
            "times can be long in larger cities such as Munich and Berlin."
        ),
        "last_scraped": "2025-01-01",
    },

    # ── Student guidance (study-in-Germany / university context) ─────────────
    {
        "source": "https://www.study-in-germany.de/en/plan-your-studies/requirements/visa/",
        "passport_nationality": "Pakistani",
        "destination_country": "Germany",
        "travel_purpose": "student",
        "title": "Studying in Germany — Visa, Blocked Account & Enrolment (Pakistani Students)",
        "content": (
            "International students from Pakistan planning to study in Germany should start the visa "
            "process as soon as they receive admission, because national visa appointments and "
            "processing can take several weeks. The blocked account (Sperrkonto) is the most common "
            "proof of financial means: the student deposits the required annual amount and may "
            "withdraw a fixed monthly sum after arrival. Students must hold valid health insurance — "
            "travel insurance for the initial period and statutory or recognised private insurance "
            "once enrolled. On arrival the student registers their address, enrols at the "
            "university, opens a bank account, and applies for the study residence permit. A study "
            "permit also allows limited part-time work (a capped number of days or half-days per "
            "year). Universities such as TUM provide an International Office that guides newly "
            "arrived students through enrolment, residence registration and the residence-permit "
            "appointment."
        ),
        "last_scraped": "2025-01-01",
    },
]
