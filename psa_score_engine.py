import json
import yaml
from collections import defaultdict

def get_psa_ontology(path="psa_ontology_comprehensive_with_alias.json"):
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    return data["SignalDomains"]

def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def match_terms(domain, text):
    all_terms = domain.get("terms", []) + domain.get("aliases", [])
    return [term for term in all_terms if term.lower() in text.lower()]

def generate_gap_analysis(resume_text, jd_text, ontology, config):
    result = []
    weights = config.get("weights", {"mli": 0.4, "signal_strength": 0.6})

    matched_domains = 0
    total_domains = len(ontology)

    for domain in ontology:
        name = domain["name"]
        jd_terms = match_terms(domain, jd_text)
        resume_terms = match_terms(domain, resume_text)

        missing_terms = list(set(jd_terms) - set(resume_terms))
        match_pct = round(len(resume_terms) / len(jd_terms), 2) if jd_terms else 0

        result.append({
            "Domain": name,
            "JD Terms": ", ".join(jd_terms),
            "Resume Terms": ", ".join(resume_terms),
            "Missing": ", ".join(missing_terms),
            "Match %": match_pct
        })

        if match_pct > 0:
            matched_domains += 1

    signal_strength = matched_domains / total_domains
    mli = 1.0 if len(resume_text.split()) >= 300 else 0.5
    score = round(
        weights["signal_strength"] * signal_strength +
        weights["mli"] * mli,
        2
    )

    return result, score
