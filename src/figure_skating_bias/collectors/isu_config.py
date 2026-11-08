"""ISU event definitions and normalized output schema."""

from __future__ import annotations

from dataclasses import dataclass

RESULTS_HOST = "results.isu.org"


@dataclass(frozen=True)
class ISUEvent:
    """An official ISU event index and its stable project identifier."""

    competition_id: str
    competition_name: str
    season: str
    event_code: str
    source_index_url: str | None = None
    trusted_hosts: tuple[str, ...] = ()

    @property
    def index_url(self) -> str:
        if self.source_index_url is not None:
            return self.source_index_url
        return f"https://{RESULTS_HOST}/results/{self.season}/{self.event_code}/index.htm"


CHAMPIONSHIP_EVENTS = (
    ISUEvent("wc2022", "World Figure Skating Championships 2022", "season2122", "wc2022"),
    ISUEvent("ec2022", "European Figure Skating Championships 2022", "season2122", "ec2022"),
    ISUEvent("fc2022", "Four Continents Figure Skating Championships 2022", "season2122", "fc2022"),
    ISUEvent("owg2022", "Olympic Winter Games 2022", "season2122", "owg2022"),
    ISUEvent("ec2023", "European Figure Skating Championships 2023", "season2223", "ec2023"),
    ISUEvent("fc2023", "Four Continents Figure Skating Championships 2023", "season2223", "fc2023"),
    ISUEvent("wc2024", "World Figure Skating Championships 2024", "season2324", "wc2024"),
    ISUEvent("ec2024", "European Figure Skating Championships 2024", "season2324", "ec2024"),
    ISUEvent("fc2024", "Four Continents Figure Skating Championships 2024", "season2324", "fc2024"),
    ISUEvent("ec2025", "European Figure Skating Championships 2025", "season2425", "ec2025"),
    ISUEvent("fc2025", "Four Continents Figure Skating Championships 2025", "season2425", "fc2025"),
    ISUEvent("wc2025", "World Figure Skating Championships 2025", "season2425", "wc2025"),
    ISUEvent("ec2026", "European Figure Skating Championships 2026", "season2526", "ec2026"),
    ISUEvent("fc2026", "Four Continents Figure Skating Championships 2026", "season2526", "fc2026"),
    ISUEvent("owg2026", "Olympic Winter Games 2026", "season2526", "owg2026"),
    ISUEvent("wc2026", "World Figure Skating Championships 2026", "season2526", "wc2026"),
)
GRAND_PRIX_EVENTS = (
    ISUEvent("gpusa2021", "ISU Grand Prix Skate America 2021", "season2122", "gpusa2021"),
    ISUEvent(
        "gpcan2021", "ISU Grand Prix Skate Canada 2021", "season2122", "gpcan2021"
    ),
    ISUEvent(
        "gpfra2021", "ISU Grand Prix Internationaux de France 2021", "season2122", "gpfra2021"
    ),
    ISUEvent("gpita2021", "ISU Grand Prix Gran Premio d'Italia 2021", "season2122", "gpita2021"),
    ISUEvent("gprus2021", "ISU Grand Prix Rostelecom Cup 2021", "season2122", "gprus2021"),
    ISUEvent("gpusa2022", "ISU Grand Prix Skate America 2022", "season2223", "gpusa2022"),
    ISUEvent(
        "gpcan2022", "ISU Grand Prix Skate Canada 2022", "season2223", "gpcan2022"
    ),
    ISUEvent(
        "gpfra2022", "ISU Grand Prix de France 2022", "season2223", "gpfra2022"
    ),
    ISUEvent(
        "gpgbr2022", "ISU Grand Prix MK John Wilson Trophy 2022", "season2223", "gpgbr2022"
    ),
    ISUEvent("gpfin2022", "ISU Grand Prix Espoo 2022", "season2223", "gpfin2022"),
    ISUEvent(
        "gpf2022", "ISU Grand Prix Final 2022", "season2223", "gpf2022"
    ),
    ISUEvent("gpusa2023", "ISU Grand Prix Skate America 2023", "season2324", "gpusa2023"),
    ISUEvent(
        "gpcan2023", "ISU Grand Prix Skate Canada 2023", "season2324", "gpcan2023"
    ),
    ISUEvent(
        "gpfra2023", "ISU Grand Prix de France 2023", "season2324", "gpfra2023"
    ),
    ISUEvent(
        "gpchn2023", "ISU Grand Prix Cup of China 2023", "season2324", "gpchn2023"
    ),
    ISUEvent("gpfin2023", "ISU Grand Prix Espoo 2023", "season2324", "gpfin2023"),
    ISUEvent(
        "gpf2023", "ISU Grand Prix Final 2023", "season2324", "gpf2023"
    ),
    ISUEvent("gpusa2024", "ISU Grand Prix Skate America 2024", "season2425", "gpusa2024"),
    ISUEvent(
        "gpcan2024", "ISU Grand Prix Skate Canada 2024", "season2425", "gpcan2024"
    ),
    ISUEvent(
        "gpfra2024", "ISU Grand Prix de France 2024", "season2425", "gpfra2024"
    ),
    ISUEvent(
        "gpchn2024", "ISU Grand Prix Cup of China 2024", "season2425", "gpchn2024"
    ),
    ISUEvent("gpjpn2024", "ISU Grand Prix NHK Trophy 2024", "season2425", "gpjpn2024"),
    ISUEvent(
        "gpfin2024", "ISU Grand Prix Finlandia Trophy 2024", "season2425", "gpfin2024"
    ),
    ISUEvent(
        "gpf2024", "ISU Grand Prix Final 2024", "season2425", "gpf2024"
    ),
    ISUEvent("gpusa2025", "ISU Grand Prix Skate America 2025", "season2526", "gpusa2025"),
    ISUEvent(
        "gpcan2025", "ISU Grand Prix Skate Canada 2025", "season2526", "gpcan2025"
    ),
    ISUEvent(
        "gpfra2025", "ISU Grand Prix de France 2025", "season2526", "gpfra2025"
    ),
    ISUEvent(
        "gpchn2025", "ISU Grand Prix Cup of China 2025", "season2526", "gpchn2025"
    ),
    ISUEvent("gpjpn2025", "ISU Grand Prix NHK Trophy 2025", "season2526", "gpjpn2025"),
    ISUEvent(
        "gpfin2025", "ISU Grand Prix Finlandia Trophy 2025", "season2526", "gpfin2025"
    ),
    ISUEvent(
        "gpf2025", "ISU Grand Prix Final 2025", "season2526", "gpf2025"
    ),
)
CHALLENGER_EVENTS = (
    ISUEvent(
        "csger2021",
        "ISU Challenger Series Nebelhorn Trophy 2021",
        "season2122",
        "csger2021",
        "https://www.isuresults.com/results/season2122/csger2021/",
        ("www.isuresults.com",),
    ),
    ISUEvent(
        "csfin2021",
        "ISU Challenger Series Finlandia Trophy 2021",
        "season2122",
        "csfin2021",
        "https://www.figureskatingresults.fi/results/2122/CSFIN2021/index.htm",
        ("www.figureskatingresults.fi",),
    ),
    ISUEvent(
        "csusa2022",
        "ISU Challenger Series U.S. International Figure Skating Classic 2022",
        "season2223",
        "csusa2022",
        "https://ijs.usfigureskating.org/leaderboard/results/2022/csusa2022/index.htm",
        ("ijs.usfigureskating.org",),
    ),
    ISUEvent(
        "csita2022",
        "ISU Challenger Series Lombardia Trophy 2022",
        "season2223",
        "csita2022",
        "https://www.fisg.it/upload/result/5874/csita2022/index.htm",
        ("www.fisg.it",),
    ),
    ISUEvent(
        "csfin2022",
        "ISU Challenger Series Finlandia Trophy 2022",
        "season2223",
        "csfin2022",
        "https://www.figureskatingresults.fi/results/2223/CSFIN2022/index.htm",
        ("www.figureskatingresults.fi",),
    ),
    ISUEvent(
        "csbud2022",
        "ISU Challenger Series Budapest Trophy 2022",
        "season2223",
        "csbud2022",
        "https://hunskate.hu/external/mukorcsolya/2022_2023/BPTrophy/index.htm",
        ("hunskate.hu",),
    ),
    ISUEvent(
        "cspol2022",
        "ISU Challenger Series Warsaw Cup 2022",
        "season2223",
        "cspol2022",
        "https://page.pfsa.com.pl/results/2223/CSPOL2022/",
        ("page.pfsa.com.pl",),
    ),
    ISUEvent(
        "csita2023",
        "ISU Challenger Series Lombardia Trophy 2023",
        "season2324",
        "csita2023",
        "https://www.fisg.it/upload/result/6185/csita2023/index.htm",
        ("www.fisg.it",),
    ),
    ISUEvent(
        "cscan2023",
        "ISU Challenger Series Autumn Classic International 2023",
        "season2324",
        "cscan2023",
        "https://skatecanada.ca/results/23aci/cscan2023/",
        ("skatecanada.ca",),
    ),
    ISUEvent(
        "csfin2023",
        "ISU Challenger Series Finlandia Trophy 2023",
        "season2324",
        "csfin2023",
        "https://www.figureskatingresults.fi/results/2324/csfin2023/index.htm",
        ("www.figureskatingresults.fi",),
    ),
    ISUEvent(
        "csbud2023",
        "ISU Challenger Series Budapest Trophy 2023",
        "season2324",
        "csbud2023",
        "https://hunskate.hu/external/mukorcsolya/2023_2024/Budtrophy/index.htm",
        ("hunskate.hu",),
    ),
    ISUEvent(
        "cspol2023",
        "ISU Challenger Series Warsaw Cup 2023",
        "season2324",
        "cspol2023",
        "https://page.pfsa.com.pl/results/2324/CSPOL2023/",
        ("page.pfsa.com.pl",),
    ),
    ISUEvent(
        "csusa2024",
        "ISU Challenger Series Cranberry Cup International 2024",
        "season2425",
        "csusa2024",
        "https://ijs.usfigureskating.org/leaderboard/results/2024/35561/index.htm",
        ("ijs.usfigureskating.org",),
    ),
    ISUEvent(
        "csusa2024jn",
        "ISU Challenger Series John Nicks International Pairs 2024",
        "season2425",
        "csusa2024jn",
        "https://ijs.usfigureskating.org/leaderboard/results/2024/35562/index.htm",
        ("ijs.usfigureskating.org",),
    ),
    ISUEvent(
        "csita2024",
        "ISU Challenger Series Lombardia Trophy 2024",
        "season2425",
        "csita2024",
        "https://www.fisg.it/upload/result/6511/online/index.htm",
        ("www.fisg.it",),
    ),
    ISUEvent(
        "csbud2024",
        "ISU Challenger Series Budapest Trophy 2024",
        "season2425",
        "csbud2024",
        "https://hunskate.hu/external/mukorcsolya/2024_2025/Budapesttrophy2024/index.htm",
        ("hunskate.hu",),
    ),
    ISUEvent(
        "cstmnca2024",
        "ISU Challenger Series Trophée Métropole Nice Côte d'Azur 2024",
        "season2425",
        "cstmnca2024",
        "https://www.ffsg.org/resultats/2024-2025/TMNCA2024/index.htm",
        ("www.ffsg.org",),
    ),
    ISUEvent(
        "csest2024",
        "ISU Challenger Series Tallinn Trophy 2024",
        "season2425",
        "csest2024",
        "https://current.fsresults.info/2024-2025/CSEST2024/index.htm",
        ("current.fsresults.info", "results.fsresults.info"),
    ),
    ISUEvent(
        "cscro2024",
        "ISU Challenger Series Golden Spin of Zagreb 2024",
        "season2425",
        "cscro2024",
        "https://www.croskate.hr/cscro2024/",
        ("www.croskate.hr",),
    ),
    ISUEvent(
        "csusa2025",
        "ISU Challenger Series Cranberry Cup International 2025",
        "season2526",
        "csusa2025",
        "https://ijs.usfigureskating.org/leaderboard/results/2025/36369/index.htm",
        ("ijs.usfigureskating.org",),
    ),
    ISUEvent(
        "csusa2025jn",
        "ISU Challenger Series John Nicks International Pairs 2025",
        "season2526",
        "csusa2025jn",
        "https://ijs.usfigureskating.org/leaderboard/results/2025/36395/index.htm",
        ("ijs.usfigureskating.org",),
    ),
    ISUEvent(
        "csjpn2025",
        "ISU Challenger Series Kinoshita Group Cup 2025",
        "season2526",
        "csjpn2025",
        "https://www.jsfresults.com/InterNational/2025-2026/csjpn2025/index.htm",
        ("www.jsfresults.com",),
    ),
    ISUEvent(
        "csita2025",
        "ISU Challenger Series Lombardia Trophy 2025",
        "season2526",
        "csita2025",
        "https://www.fisg.it/upload/result/6845/online/index.htm",
        ("www.fisg.it",),
    ),
)
TARGET_EVENTS = (*CHAMPIONSHIP_EVENTS, *GRAND_PRIX_EVENTS, *CHALLENGER_EVENTS)
EVENT_CATEGORIES = {
    "FSKMSINGLES": "men_singles",
    "FSKWSINGLES": "women_singles",
    "FSKXPAIRS": "pair_skating",
    "FSKXICEDANCE": "ice_dance",
}
OUTPUT_COLUMNS = [
    "competition_id",
    "competition_name",
    "season",
    "scoring_rule_version",
    "event_category",
    "event_type",
    "segment",
    "entry_id",
    "entry_name",
    "entry_nationality",
    "rank",
    "total_segment_score",
    "total_element_score",
    "program_component_score",
    "total_deductions",
    "judge_id",
    "judge_panel_assignment",
    "judge_name",
    "judge_nationality",
    "judge_federation",
    "judge_federation_match",
    "judge_federation_source_url",
    "mark_type",
    "element_number",
    "element_type",
    "base_value",
    "technical_call",
    "goe_total",
    "component",
    "component_factor",
    "score",
    "panel_mean",
    "panel_median",
    "source_url",
    "source_file",
    "source_sha256",
]
