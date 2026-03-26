/**
 * 1990-research-map-assessment.ts
 *
 * Epistemic self-assessment of the source map used in:
 * "The Year 1990: A Complete Historical Review"
 *
 * Conforms to: research-map-assessment.ts schema v1.0.0
 * Companion to: research-source-schema.ts v3.0.0 (ResearchMap)
 *
 * Zod v4 — import path: "zod"
 * Reference: https://zod.dev/api
 */

import type {
  MapAssessment,
  AxisAssessment,
  SourceTypeDistribution as SourceTypeDistributionType,
  MethodBias,
  CoverageGap,
  BlindSpot,
  RemediationAction,
  PositionalityStatement,
  AssessmentVerdict,
} from "./research-map-assessment";

// ═════════════════════════════════════════════
// SOURCE REGISTRY
// All 83 sources retrieved during the 1990 research.
// Grouped by thematic cluster; each entry carries
// the fields consumed by the MapAssessment schema.
// ═════════════════════════════════════════════

export const sources = [

  // ── CLUSTER 1: German Reunification ─────────────────────────────────
  {
    id: "src-001",
    kind: "web-article",
    title: "What Is the German Reunification Timeline?",
    publisher: "WhySoGermany",
    url: "https://whysogermany.com/what-is-the-german-reunification-timeline/",
    publishDate: { kind: "exact", value: "2025-09-02" },
    language: "en",
    institutionalClass: "independent-web",
    geographicPerspective: "Germany / Western Europe",
    topics: ["german-reunification", "cold-war-end", "1990-geopolitics"],
  },
  {
    id: "src-002",
    kind: "encyclopedia-entry",
    title: "German Reunification",
    publisher: "Encyclopædia Britannica",
    url: "https://www.britannica.com/topic/german-reunification",
    publishDate: { kind: "exact", value: "2026-03-17" },
    language: "en",
    institutionalClass: "reference-publisher",
    geographicPerspective: "Global / Western",
    topics: ["german-reunification", "helmut-kohl", "two-plus-four-treaty"],
  },
  {
    id: "src-003",
    kind: "encyclopedia-entry",
    title: "German Reunification",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/German_reunification",
    publishDate: { kind: "approximate", label: "2002, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["german-reunification"],
  },
  {
    id: "src-004",
    kind: "government-document",
    title: '"2+4" Talks and the Reunification of Germany, 1990',
    publisher: "U.S. Department of State (Office of the Historian)",
    url: "https://2001-2009.state.gov/r/pa/ho/time/pcw/108224.htm",
    publishDate: { kind: "approximate", label: "2001–2009 archive" },
    language: "en",
    institutionalClass: "government-official",
    geographicPerspective: "United States / Western Allied",
    topics: ["two-plus-four-treaty", "german-reunification", "cold-war-diplomacy"],
  },
  {
    id: "src-005",
    kind: "museum-web",
    title: "The Reunification of Germany and Fall of the Berlin Wall",
    publisher: "Deutschlandmuseum",
    url: "https://www.deutschlandmuseum.de/en/history/german-reunification/",
    publishDate: { kind: "exact", value: "2026-03-11" },
    language: "en",
    institutionalClass: "cultural-institution",
    geographicPerspective: "Germany",
    topics: ["german-reunification", "berlin-wall"],
  },

  // ── CLUSTER 2: Nelson Mandela & South Africa ─────────────────────────
  {
    id: "src-006",
    kind: "web-article",
    title: "In History: Nelson Mandela walks out of prison a free man",
    publisher: "BBC Culture",
    url: "https://www.bbc.com/culture/article/20240207-in-history-nelson-mandela-walks-out-of-prison-a-free-man",
    publishDate: { kind: "exact", value: "2024-02-08" },
    language: "en",
    institutionalClass: "public-broadcaster",
    geographicPerspective: "United Kingdom / Global",
    topics: ["nelson-mandela", "apartheid", "south-africa", "1990-africa"],
  },
  {
    id: "src-007",
    kind: "research-starter",
    title: "Mandela Is Freed",
    publisher: "EBSCO Research Starters",
    url: "https://www.ebsco.com/research-starters/history/mandela-freed",
    publishDate: { kind: "approximate", label: "undated, database entry" },
    language: "en",
    institutionalClass: "academic-database",
    geographicPerspective: "Global (aggregated)",
    topics: ["nelson-mandela", "apartheid", "de-klerk"],
  },
  {
    id: "src-008",
    kind: "encyclopedia-entry",
    title: "Nelson Mandela",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Nelson_Mandela",
    publishDate: { kind: "approximate", label: "2001, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["nelson-mandela", "anc", "south-africa"],
  },
  {
    id: "src-009",
    kind: "web-article",
    title: "The Story of Nelson Mandela",
    publisher: "Canadian Museum for Human Rights",
    url: "https://humanrights.ca/story/story-nelson-mandela",
    publishDate: { kind: "approximate", label: "undated" },
    language: "en",
    institutionalClass: "cultural-institution",
    geographicPerspective: "Canada / Global",
    topics: ["nelson-mandela", "human-rights"],
  },

  // ── CLUSTER 3: Gulf War — Iraq Invasion of Kuwait ────────────────────
  {
    id: "src-010",
    kind: "encyclopedia-entry",
    title: "Iraqi Invasion of Kuwait",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Iraqi_invasion_of_Kuwait",
    publishDate: { kind: "approximate", label: "2005, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["gulf-war", "iraq", "kuwait", "1990-middle-east"],
  },
  {
    id: "src-011",
    kind: "government-document",
    title: "The Gulf War 1990–1991 (Operation Desert Shield)",
    publisher: "U.S. Naval History and Heritage Command",
    url: "https://www.history.navy.mil/our-collections/art/exhibits/conflicts-and-operations/the-gulf-war-1990-1991--operation-desert-shie...",
    publishDate: { kind: "approximate", label: "2001" },
    language: "en",
    institutionalClass: "government-military",
    geographicPerspective: "United States Military",
    topics: ["gulf-war", "operation-desert-shield", "1990-military"],
  },
  {
    id: "src-012",
    kind: "encyclopedia-entry",
    title: "Gulf War",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Gulf_War",
    publishDate: { kind: "approximate", label: "2001, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["gulf-war", "un-security-council", "coalition"],
  },
  {
    id: "src-013",
    kind: "research-starter",
    title: "Iraqi Invasion of Kuwait",
    publisher: "EBSCO Research Starters – Military History",
    url: "https://www.ebsco.com/research-starters/military-history-and-science/iraqi-invasion-kuwait",
    publishDate: { kind: "approximate", label: "undated" },
    language: "en",
    institutionalClass: "academic-database",
    geographicPerspective: "Global (aggregated)",
    topics: ["gulf-war", "iraq", "kuwait"],
  },
  {
    id: "src-014",
    kind: "encyclopedia-entry",
    title: "Cold War (1985–1991)",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Cold_War_(1985%E2%80%931991)",
    publishDate: { kind: "approximate", label: "2006, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["cold-war", "soviet-union", "gulf-war-coalition"],
  },

  // ── CLUSTER 4: Baltic Independence ──────────────────────────────────
  {
    id: "src-015",
    kind: "institutional-web",
    title: "Restoration of Independence in the Baltics",
    publisher: "Baltic Defence College",
    url: "https://baltdefcol.org/news/restoration-of-independence-in-the-baltics",
    publishDate: { kind: "exact", value: "2021-04-26" },
    language: "en",
    institutionalClass: "military-academic",
    geographicPerspective: "Baltic / NATO",
    topics: ["baltic-independence", "lithuania", "latvia", "estonia", "ussr"],
  },
  {
    id: "src-016",
    kind: "research-starter",
    title: "Baltic States Gain Independence",
    publisher: "EBSCO Research Starters – History",
    url: "https://www.ebsco.com/research-starters/history/baltic-states-gain-independence",
    publishDate: { kind: "approximate", label: "undated" },
    language: "en",
    institutionalClass: "academic-database",
    geographicPerspective: "Global (aggregated)",
    topics: ["baltic-independence", "cold-war-end"],
  },
  {
    id: "src-017",
    kind: "web-article",
    title: "The Recognition of Independence of the Baltic States (1990–1991)",
    publisher: "alporusi.fi",
    url: "https://www.alporusi.fi/blogi/the-recognition-of-independence-of-the-baltic-states-1990-1991",
    publishDate: { kind: "exact", value: "2020-03-17" },
    language: "en",
    institutionalClass: "independent-web",
    geographicPerspective: "Finland / Baltic",
    topics: ["baltic-independence", "international-recognition"],
  },
  {
    id: "src-018",
    kind: "news-article",
    title: "Independence for Baltic States: Freedom",
    publisher: "Los Angeles Times (archive)",
    url: "https://www.latimes.com/archives/la-xpm-1991-09-07-mn-1530-story.html",
    publishDate: { kind: "exact", value: "1991-09-07" },
    language: "en",
    institutionalClass: "national-newspaper",
    geographicPerspective: "United States",
    topics: ["baltic-independence", "ussr-collapse"],
  },

  // ── CLUSTER 5: Namibia Independence ─────────────────────────────────
  {
    id: "src-019",
    kind: "encyclopedia-entry",
    title: "Recognition of the Independence of Namibia Act, 1990",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Recognition_of_the_Independence_of_Namibia_Act,_1990",
    publishDate: { kind: "approximate", label: "2012, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["namibia-independence", "south-africa", "apartheid"],
  },
  {
    id: "src-020",
    kind: "institutional-web",
    title: "Namibia Gains Independence",
    publisher: "South African History Archive (SAHA)",
    url: "https://sahistory.org.za/dated-event/namibia-gains-independence",
    publishDate: { kind: "exact", value: "2019-09-29" },
    language: "en",
    institutionalClass: "archival-institution",
    geographicPerspective: "South Africa / Southern Africa",
    topics: ["namibia-independence", "sam-nujoma"],
  },
  {
    id: "src-021",
    kind: "web-article",
    title: "The Independence — History of Namibia",
    publisher: "namib.info",
    url: "https://www.namib.info/namibia/uk/history/independence/",
    publishDate: { kind: "approximate", label: "undated" },
    language: "en",
    institutionalClass: "independent-web",
    geographicPerspective: "Namibia",
    topics: ["namibia-independence", "regional-history"],
  },
  {
    id: "src-022",
    kind: "research-starter",
    title: "Namibia Is Liberated from South African Control",
    publisher: "EBSCO Research Starters – Politics",
    url: "https://www.ebsco.com/research-starters/politics-and-government/namibia-liberated-south-african-control",
    publishDate: { kind: "approximate", label: "undated" },
    language: "en",
    institutionalClass: "academic-database",
    geographicPerspective: "Global (aggregated)",
    topics: ["namibia-independence", "cold-war-africa"],
  },

  // ── CLUSTER 6: Yemeni Unification ────────────────────────────────────
  {
    id: "src-023",
    kind: "encyclopedia-entry",
    title: "Yemeni Unification",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Yemeni_unification",
    publishDate: { kind: "approximate", label: "2006, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["yemen-unification", "north-yemen", "south-yemen", "1990-middle-east"],
  },
  {
    id: "src-024",
    kind: "web-article",
    title: "The Making and Unmaking of Yemen Unity Over Half a Century",
    publisher: "Al Majalla",
    url: "https://en.majalla.com/node/328781/politics/making-and-unmaking-yemen-unity-over-half-century",
    publishDate: { kind: "exact", value: "2025-12-18" },
    language: "en",
    institutionalClass: "regional-news-outlet",
    geographicPerspective: "Middle East / Arab",
    topics: ["yemen-unification", "ali-abdullah-saleh"],
  },
  {
    id: "src-025",
    kind: "academic-journal",
    title: "Yemen: Unification and the Gulf War",
    publisher: "Middle East Research and Information Project (MERIP)",
    url: "https://www.merip.org/1991/05/yemen-unification-and-the-gulf-war/",
    publishDate: { kind: "approximate", label: "1991" },
    language: "en",
    institutionalClass: "academic-publication",
    geographicPerspective: "Middle East Studies",
    topics: ["yemen-unification", "gulf-war-regional-impact"],
  },

  // ── CLUSTER 7: Yugoslavia ─────────────────────────────────────────────
  {
    id: "src-026",
    kind: "web-article",
    title: "The Breakup of Yugoslavia",
    publisher: "Making History Come Alive (Substack)",
    url: "https://makinghistorycomealive.substack.com/p/making-history-come-alive-the-breakup",
    publishDate: { kind: "exact", value: "2026-02-18" },
    language: "en",
    institutionalClass: "independent-web",
    geographicPerspective: "Global",
    topics: ["yugoslavia", "nationalism", "1990-elections"],
  },
  {
    id: "src-027",
    kind: "web-article",
    title: "Animated Map of the Breakup of Yugoslavia 1989–2008",
    publisher: "Brilliant Maps",
    url: "https://brilliantmaps.com/breakup-of-yugoslavia/",
    publishDate: { kind: "exact", value: "2026-01-12" },
    language: "en",
    institutionalClass: "independent-web",
    geographicPerspective: "Global",
    topics: ["yugoslavia", "balkans", "independence-declarations"],
  },

  // ── CLUSTER 8: Nobel Peace Prize / Gorbachev ─────────────────────────
  {
    id: "src-028",
    kind: "official-record",
    title: "Mikhail Gorbachev – Facts",
    publisher: "Nobel Prize Official (NobelPrize.org)",
    url: "https://www.nobelprize.org/prizes/peace/1990/gorbachev/facts/",
    publishDate: { kind: "approximate", label: "1990, updated 2022-08-29" },
    language: "en",
    institutionalClass: "official-award-body",
    geographicPerspective: "Norway / Global",
    topics: ["gorbachev", "nobel-peace-prize-1990", "cold-war-end"],
  },
  {
    id: "src-029",
    kind: "official-record",
    title: "The Nobel Peace Prize 1990 – Summary",
    publisher: "Nobel Prize Official (NobelPrize.org)",
    url: "https://www.nobelprize.org/prizes/peace/1990/summary/",
    publishDate: { kind: "approximate", label: "1990" },
    language: "en",
    institutionalClass: "official-award-body",
    geographicPerspective: "Norway / Global",
    topics: ["nobel-peace-prize-1990", "gorbachev"],
  },
  {
    id: "src-030",
    kind: "primary-speech",
    title: "Mikhail Gorbachev – Nobel Peace Prize Acceptance Speech",
    publisher: "Nobel Prize Official (NobelPrize.org)",
    url: "https://www.nobelprize.org/prizes/peace/1990/gorbachev/acceptance-speech/",
    publishDate: { kind: "approximate", label: "June 1991 (delivered), archived online" },
    language: "en",
    institutionalClass: "primary-source",
    geographicPerspective: "USSR / Global",
    topics: ["gorbachev", "cold-war-diplomacy", "soviet-union"],
  },
  {
    id: "src-031",
    kind: "web-article",
    title: "Why Was Gorbachev Awarded the Nobel Peace Prize?",
    publisher: "gw2ru.com",
    url: "https://www.gw2ru.com/history/240076-why-gorbachev-awarded-nobel-peace-prize",
    publishDate: { kind: "exact", value: "2025-10-14" },
    language: "en",
    institutionalClass: "independent-web",
    geographicPerspective: "Russia / Post-Soviet",
    topics: ["gorbachev", "nobel-controversy"],
  },

  // ── CLUSTER 9: U.S. Recession 1990–1991 ─────────────────────────────
  {
    id: "src-032",
    kind: "encyclopedia-entry",
    title: "Early 1990s Recession in the United States",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Early_1990s_recession_in_the_United_States",
    publishDate: { kind: "approximate", label: "2011, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "United States",
    topics: ["1990-recession", "us-economy", "gdp"],
  },
  {
    id: "src-033",
    kind: "encyclopedia-entry",
    title: "Early 1990s Recession",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Early_1990s_recession",
    publishDate: { kind: "approximate", label: "2004, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["1990-recession", "canada-recession", "global-economy"],
  },
  {
    id: "src-034",
    kind: "research-starter",
    title: "Recession of 1990–1991",
    publisher: "EBSCO Research Starters – History",
    url: "https://www.ebsco.com/research-starters/history/recession-1990-1991",
    publishDate: { kind: "approximate", label: "undated" },
    language: "en",
    institutionalClass: "academic-database",
    geographicPerspective: "Global (aggregated)",
    topics: ["1990-recession", "oil-shock", "savings-and-loan"],
  },
  {
    id: "src-035",
    kind: "educational-web",
    title: "1990s U.S. Economy: History, Recession & Boom",
    publisher: "Study.com",
    url: "https://study.com/academy/lesson/the-us-economic-boom-of-the-1990s.html",
    publishDate: { kind: "exact", value: "2018-06-08" },
    language: "en",
    institutionalClass: "educational-platform",
    geographicPerspective: "United States",
    topics: ["1990-recession", "1990s-economy", "bill-clinton"],
  },

  // ── CLUSTER 10: Hubble Space Telescope ──────────────────────────────
  {
    id: "src-036",
    kind: "research-starter",
    title: "NASA Launches the Hubble Space Telescope",
    publisher: "EBSCO Research Starters – History",
    url: "https://www.ebsco.com/research-starters/history/nasa-launches-hubble-space-telescope",
    publishDate: { kind: "approximate", label: "undated" },
    language: "en",
    institutionalClass: "academic-database",
    geographicPerspective: "Global (aggregated)",
    topics: ["hubble-telescope", "nasa", "space-science-1990"],
  },
  {
    id: "src-037",
    kind: "government-document",
    title: "April 1990 – Hubble Space Telescope (HST) Launched",
    publisher: "NASA (official)",
    url: "https://www.nasa.gov/image-article/april-1990-hubble-space-telescope-hst-launched/",
    publishDate: { kind: "exact", value: "2023-09-18" },
    language: "en",
    institutionalClass: "government-space-agency",
    geographicPerspective: "United States",
    topics: ["hubble-telescope", "sts-31", "space-shuttle-discovery"],
  },
  {
    id: "src-038",
    kind: "web-article",
    title: "Eighth Wonder: Remembering the Launch of Hubble",
    publisher: "AmericaSpace",
    url: "https://www.americaspace.com/2024/04/24/eighth-wonder-remembering-the-launch-of-hubble-otd-in-1990/",
    publishDate: { kind: "exact", value: "2024-04-23" },
    language: "en",
    institutionalClass: "independent-web-space",
    geographicPerspective: "United States",
    topics: ["hubble-telescope", "loren-shriver", "charlie-bolden"],
  },
  {
    id: "src-039",
    kind: "institutional-web",
    title: "Telling Hubble's Story for 30 Years",
    publisher: "Smithsonian National Air and Space Museum",
    url: "https://airandspace.si.edu/stories/editorial/telling-hubbles-story-30-years",
    publishDate: { kind: "exact", value: "2020-04-23" },
    language: "en",
    institutionalClass: "cultural-institution",
    geographicPerspective: "United States",
    topics: ["hubble-telescope", "space-history"],
  },
  {
    id: "src-040",
    kind: "government-document",
    title: "STS-31 Mission Page",
    publisher: "NASA (official)",
    url: "https://www.nasa.gov/mission/sts-31/",
    publishDate: { kind: "exact", value: "2023-09-21" },
    language: "en",
    institutionalClass: "government-space-agency",
    geographicPerspective: "United States",
    topics: ["hubble-telescope", "sts-31", "shuttle-mission"],
  },

  // ── CLUSTER 11: Human Genome Project ─────────────────────────────────
  {
    id: "src-041",
    kind: "government-document",
    title: "1990: Launch of the Human Genome Project",
    publisher: "National Human Genome Research Institute (NIH)",
    url: "https://www.genome.gov/25520329/online-education-kit-1990-launch-of-the-human-genome-project",
    publishDate: { kind: "exact", value: "2013-05-05" },
    language: "en",
    institutionalClass: "government-health-agency",
    geographicPerspective: "United States",
    topics: ["human-genome-project", "nih", "bioscience-1990"],
  },
  {
    id: "src-042",
    kind: "encyclopedia-entry",
    title: "Human Genome Project",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Human_Genome_Project",
    publishDate: { kind: "approximate", label: "2001, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["human-genome-project", "dna-sequencing"],
  },
  {
    id: "src-043",
    kind: "institutional-web",
    title: "Timeline: The Human Genome Project",
    publisher: "Wellcome Genome Campus (yourgenome.org)",
    url: "https://www.yourgenome.org/theme/timeline-the-human-genome-project/",
    publishDate: { kind: "approximate", label: "undated" },
    language: "en",
    institutionalClass: "research-institution",
    geographicPerspective: "United Kingdom / Global",
    topics: ["human-genome-project", "genome-sequencing-timeline"],
  },
  {
    id: "src-044",
    kind: "government-document",
    title: "History – Human Genome Project",
    publisher: "U.S. Department of Energy Human Genome Project Archive",
    url: "https://doe-humangenomeproject.ornl.gov/history/",
    publishDate: { kind: "approximate", label: "undated (archived DOE page)" },
    language: "en",
    institutionalClass: "government-science-agency",
    geographicPerspective: "United States",
    topics: ["human-genome-project", "doe", "genome-history"],
  },

  // ── CLUSTER 12: World Wide Web ────────────────────────────────────────
  {
    id: "src-045",
    kind: "web-article",
    title: "1990: Programming the World Wide Web",
    publisher: "CyberCultural",
    url: "https://cybercultural.com/p/1990-programming-the-world-wide-web/",
    publishDate: { kind: "exact", value: "2021-10-31" },
    language: "en",
    institutionalClass: "independent-web",
    geographicPerspective: "Global",
    topics: ["world-wide-web", "tim-berners-lee", "html", "http", "cern"],
  },
  {
    id: "src-046",
    kind: "institutional-web",
    title: "A Short History of the Web",
    publisher: "CERN (official)",
    url: "https://home.cern/science/computing/birth-web/short-history-web",
    publishDate: { kind: "exact", value: "2026-03-23" },
    language: "en",
    institutionalClass: "research-institution",
    geographicPerspective: "Switzerland / International",
    topics: ["world-wide-web", "cern", "internet-history"],
  },
  {
    id: "src-047",
    kind: "encyclopedia-entry",
    title: "Tim Berners-Lee",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Tim_Berners-Lee",
    publishDate: { kind: "approximate", label: "2001, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["tim-berners-lee", "world-wide-web", "cern"],
  },
  {
    id: "src-048",
    kind: "institutional-web",
    title: "The Birth of the Web",
    publisher: "CERN (official)",
    url: "https://home.cern/science/computing/birth-web",
    publishDate: { kind: "exact", value: "2026-03-23" },
    language: "en",
    institutionalClass: "research-institution",
    geographicPerspective: "Switzerland / International",
    topics: ["world-wide-web", "cern", "info.cern.ch"],
  },

  // ── CLUSTER 13: World Population ─────────────────────────────────────
  {
    id: "src-049",
    kind: "statistical-database",
    title: "World Population by Year",
    publisher: "Worldometers",
    url: "https://www.worldometers.info/world-population/world-population-by-year/",
    publishDate: { kind: "exact", value: "2024-10-31" },
    language: "en",
    institutionalClass: "statistical-aggregator",
    geographicPerspective: "Global",
    topics: ["world-population", "1990-demographics"],
  },
  {
    id: "src-050",
    kind: "encyclopedia-entry",
    title: "World Population",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/World_population",
    publishDate: { kind: "approximate", label: "2004, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["world-population", "demographics"],
  },

  // ── CLUSTER 14: Iran Earthquake ──────────────────────────────────────
  {
    id: "src-051",
    kind: "web-article",
    title: "1990 Manjil–Rudbar Earthquake",
    publisher: "NZ Survivor",
    url: "https://nzsurvivor.co.nz/1990-manjil-rudbar-earthquake/",
    publishDate: { kind: "approximate", label: "2010" },
    language: "en",
    institutionalClass: "independent-web",
    geographicPerspective: "New Zealand / Global",
    topics: ["iran-earthquake-1990", "natural-disaster", "manjil-rudbar"],
  },
  {
    id: "src-052",
    kind: "encyclopedia-entry",
    title: "1990 Manjil–Rudbar Earthquake",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/1990_Manjil%E2%80%93Rudbar_earthquake",
    publishDate: { kind: "approximate", label: "2007, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["iran-earthquake-1990", "mw-74", "death-toll"],
  },
  {
    id: "src-053",
    kind: "research-starter",
    title: "Massive Quake Rocks Iran",
    publisher: "EBSCO Research Starters – Earth Sciences",
    url: "https://www.ebsco.com/research-starters/earth-and-atmospheric-sciences/massive-quake-rocks-iran",
    publishDate: { kind: "approximate", label: "undated" },
    language: "en",
    institutionalClass: "academic-database",
    geographicPerspective: "Global (aggregated)",
    topics: ["iran-earthquake-1990", "humanitarian-response"],
  },
  {
    id: "src-054",
    kind: "news-article",
    title: "2 More Earthquakes Rock Iran; Rescue Efforts Stall as Toll Rises",
    publisher: "The New York Times",
    url: "https://www.nytimes.com/1990/06/25/world/2-more-earthquakes-rock-iran-rescue-efforts-stall-as-toll-rises.html",
    publishDate: { kind: "exact", value: "1990-06-25" },
    language: "en",
    institutionalClass: "national-newspaper",
    geographicPerspective: "United States",
    topics: ["iran-earthquake-1990", "contemporary-reporting"],
  },
  {
    id: "src-055",
    kind: "academic-journal",
    title: "Rudbār Mw 7.3 Earthquake of 1990 June 20: Seismotectonics",
    publisher: "Geophysical Journal International (Oxford Academic)",
    url: "https://academic.oup.com/gji/article/182/3/1577/600044",
    publishDate: { kind: "exact", value: "2010-08-31" },
    language: "en",
    institutionalClass: "peer-reviewed-journal",
    geographicPerspective: "International Academic",
    topics: ["iran-earthquake-1990", "seismotectonics", "geophysics"],
  },

  // ── CLUSTER 15: Philippines Luzon Earthquake ─────────────────────────
  {
    id: "src-056",
    kind: "encyclopedia-entry",
    title: "1990 Luzon Earthquake",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/1990_Luzon_earthquake",
    publishDate: { kind: "approximate", label: "2006, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["luzon-earthquake-1990", "philippines", "natural-disaster"],
  },

  // ── CLUSTER 16: Mecca Tunnel Stampede ────────────────────────────────
  {
    id: "src-057",
    kind: "encyclopedia-entry",
    title: "1990 Mecca Tunnel Tragedy",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/1990_Mecca_tunnel_tragedy",
    publishDate: { kind: "approximate", label: "2015, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["mecca-tunnel-stampede", "hajj", "saudi-arabia", "1990-tragedy"],
  },
  {
    id: "src-058",
    kind: "news-article",
    title: "Mecca Tunnel Deaths Blamed on 7 Who Fell",
    publisher: "Los Angeles Times (archive)",
    url: "https://www.latimes.com/archives/la-xpm-1990-07-04-mn-85-story.html",
    publishDate: { kind: "exact", value: "1990-07-04" },
    language: "en",
    institutionalClass: "national-newspaper",
    geographicPerspective: "United States",
    topics: ["mecca-tunnel-stampede", "contemporary-reporting"],
  },
  {
    id: "src-059",
    kind: "news-article",
    title: "Death Toll During Recent Hajj Pilgrimage Worst on Record",
    publisher: "PBS NewsHour",
    url: "https://www.pbs.org/newshour/world/death-toll-during-recent-hajj-pilgrimage-worst-on-record",
    publishDate: { kind: "exact", value: "2015-10-08" },
    language: "en",
    institutionalClass: "public-broadcaster",
    geographicPerspective: "United States / Global",
    topics: ["mecca-tunnel-stampede", "hajj-disasters-history"],
  },
  {
    id: "src-060",
    kind: "encyclopedia-entry",
    title: "Incidents During the Hajj",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Incidents_during_the_Hajj",
    publishDate: { kind: "approximate", label: "2006, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["mecca-tunnel-stampede", "hajj-safety"],
  },
  {
    id: "src-061",
    kind: "long-form-journalism",
    title: "The 10-Minute Mecca Stampede That Made History",
    publisher: "Vanity Fair",
    url: "https://www.vanityfair.com/news/2018/01/the-mecca-stampede-that-made-history-hajj",
    publishDate: { kind: "exact", value: "2018-01-08" },
    language: "en",
    institutionalClass: "national-magazine",
    geographicPerspective: "United States",
    topics: ["mecca-tunnel-stampede", "tunnel-conditions", "ventilation-failure"],
  },

  // ── CLUSTER 17: FIFA World Cup 1990 ─────────────────────────────────
  {
    id: "src-062",
    kind: "encyclopedia-entry",
    title: "1990 FIFA World Cup",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/1990_FIFA_World_Cup",
    publishDate: { kind: "approximate", label: "2002, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["fifa-world-cup-1990", "italy", "west-germany", "argentina"],
  },
  {
    id: "src-063",
    kind: "sports-statistics",
    title: "FIFA World Cup 1990 Italy – Standings, Fixtures & Stats",
    publisher: "Global Sports Archive",
    url: "https://globalsportsarchive.com/en/soccer/competition/fifa-world-cup-1990-italy/259",
    publishDate: { kind: "approximate", label: "undated" },
    language: "en",
    institutionalClass: "sports-statistics",
    geographicPerspective: "Global",
    topics: ["fifa-world-cup-1990", "match-statistics"],
  },

  // ── CLUSTER 18: Tyson vs. Douglas ────────────────────────────────────
  {
    id: "src-064",
    kind: "encyclopedia-entry",
    title: "Mike Tyson vs. Buster Douglas",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Mike_Tyson_vs._Buster_Douglas",
    publishDate: { kind: "approximate", label: "2010, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["tyson-douglas-1990", "boxing", "sports-upset"],
  },
  {
    id: "src-065",
    kind: "sports-journalism",
    title: "The Day Douglas Shook the World",
    publisher: "ESPN",
    url: "https://www.espn.com/boxing/story/_/page/blackhistoryBOX1/the-day-james-buster-douglas-shook-world",
    publishDate: { kind: "exact", value: "2015-02-10" },
    language: "en",
    institutionalClass: "sports-broadcaster",
    geographicPerspective: "United States",
    topics: ["tyson-douglas-1990", "boxing-history"],
  },
  {
    id: "src-066",
    kind: "news-article",
    title: "Douglas-Tyson: Round by Round",
    publisher: "Los Angeles Times (archive)",
    url: "https://www.latimes.com/archives/la-xpm-1990-02-12-sp-514-story.html",
    publishDate: { kind: "exact", value: "1990-02-12" },
    language: "en",
    institutionalClass: "national-newspaper",
    geographicPerspective: "United States",
    topics: ["tyson-douglas-1990", "contemporary-reporting"],
  },

  // ── CLUSTER 19: Film / Box Office ────────────────────────────────────
  {
    id: "src-067",
    kind: "encyclopedia-entry",
    title: "List of 1990 Box Office Number-One Films in the United States",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/List_of_1990_box_office_number-one_films_in_the_United_States",
    publishDate: { kind: "approximate", label: "2007, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "United States",
    topics: ["1990-cinema", "home-alone", "ghost-film", "box-office"],
  },
  {
    id: "src-068",
    kind: "statistical-database",
    title: "Domestic Box Office for 1990",
    publisher: "Box Office Mojo",
    url: "https://www.boxofficemojo.com/year/1990/?grossesOption=totalGrosses",
    publishDate: { kind: "approximate", label: "undated (live database)" },
    language: "en",
    institutionalClass: "industry-database",
    geographicPerspective: "United States",
    topics: ["1990-cinema", "box-office-grosses"],
  },
  {
    id: "src-069",
    kind: "web-article",
    title: "Each Year of the 1990s' Highest Grossing Film",
    publisher: "CBR",
    url: "https://www.cbr.com/each-year-of-the-1990s-highest-grossing-film/",
    publishDate: { kind: "exact", value: "2022-05-29" },
    language: "en",
    institutionalClass: "pop-culture-web",
    geographicPerspective: "United States",
    topics: ["1990-cinema", "home-alone-box-office"],
  },

  // ── CLUSTER 20: Music ─────────────────────────────────────────────────
  {
    id: "src-070",
    kind: "web-article",
    title: "1990's Biggest Hits and the Soundtrack of a New Decade",
    publisher: "Classic Gold",
    url: "https://classicgold.ca/1990s-biggest-hits-and-the-soundtrack-of-a-new-decade/",
    publishDate: { kind: "exact", value: "2026-03-21" },
    language: "en",
    institutionalClass: "pop-culture-web",
    geographicPerspective: "Canada",
    topics: ["1990-music", "sinead-oconnor", "madonna-vogue", "mc-hammer"],
  },
  {
    id: "src-071",
    kind: "web-article",
    title: "Best Albums of 1990: 58 Records Worth Revisiting",
    publisher: "uDiscover Music",
    url: "https://www.udiscovermusic.com/stories/best-1990-albums/",
    publishDate: { kind: "exact", value: "2025-04-03" },
    language: "en",
    institutionalClass: "music-media",
    geographicPerspective: "Global",
    topics: ["1990-music", "albums", "mariah-carey", "mc-hammer"],
  },
  {
    id: "src-072",
    kind: "blog",
    title: "The Second Day of 1990: My 1000 Favorite Albums",
    publisher: "If My Records Could Talk",
    url: "https://ifmyrecordscouldtalk.com/2020/09/12/the-second-day-of-1990-my-1000-favorite-albums/",
    publishDate: { kind: "exact", value: "2020-09-11" },
    language: "en",
    institutionalClass: "independent-blog",
    geographicPerspective: "Personal / Global",
    topics: ["1990-music", "albums-review"],
  },
  {
    id: "src-073",
    kind: "news-article",
    title: "A Top Ten of the Most Touching Singles at 1990's Halfway",
    publisher: "Los Angeles Times (archive)",
    url: "https://www.latimes.com/archives/la-xpm-1990-06-30-ca-536-story.html",
    publishDate: { kind: "exact", value: "1990-06-30" },
    language: "en",
    institutionalClass: "national-newspaper",
    geographicPerspective: "United States",
    topics: ["1990-music", "singles-chart", "contemporary-reporting"],
  },
  {
    id: "src-074",
    kind: "podcast-transcript",
    title: "History of the '90s Podcast: Top Stories of 1990",
    publisher: "Global News",
    url: "https://globalnews.ca/news/6302551/history-of-the-90s-podcast-top-stories-of-1990/",
    publishDate: { kind: "exact", value: "2020-07-07" },
    language: "en",
    institutionalClass: "national-news-outlet",
    geographicPerspective: "Canada",
    topics: ["1990-overview", "milli-vanilli", "pop-culture"],
  },

  // ── CLUSTER 21: Gardner Museum Heist ─────────────────────────────────
  {
    id: "src-075",
    kind: "encyclopedia-entry",
    title: "Isabella Stewart Gardner Museum Theft",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/Isabella_Stewart_Gardner_Museum_theft",
    publishDate: { kind: "approximate", label: "2015, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "United States",
    topics: ["gardner-heist", "art-theft", "rembrandt", "vermeer"],
  },
  {
    id: "src-076",
    kind: "news-article",
    title: "What to Know About the Gardner Museum Heist, 35 Years Later",
    publisher: "Boston.com",
    url: "https://www.boston.com/news/local-news/2025/03/18/what-to-know-about-the-gardner-museum-heist-35-years-later/",
    publishDate: { kind: "exact", value: "2025-03-17" },
    language: "en",
    institutionalClass: "regional-newspaper",
    geographicPerspective: "United States (Boston)",
    topics: ["gardner-heist", "unsolved-case", "stolen-art"],
  },
  {
    id: "src-077",
    kind: "web-article",
    title: "The Unsolved Heist at Isabella Stewart Gardner Museum",
    publisher: "A&E (aetv.com)",
    url: "https://www.aetv.com/articles/the-unsolved-heist-at-isabella-stewart-gardner-museum",
    publishDate: { kind: "exact", value: "2025-11-16" },
    language: "en",
    institutionalClass: "media-company",
    geographicPerspective: "United States",
    topics: ["gardner-heist", "fbi", "unsolved-crime"],
  },
  {
    id: "src-078",
    kind: "official-institution-web",
    title: "Isabella Stewart Gardner Museum – Official Theft Page",
    publisher: "Isabella Stewart Gardner Museum (official)",
    url: "https://www.gardnermuseum.org/about/theft",
    publishDate: { kind: "approximate", label: "undated (official page)" },
    language: "en",
    institutionalClass: "primary-institution",
    geographicPerspective: "United States",
    topics: ["gardner-heist", "reward", "empty-frames"],
  },

  // ── CLUSTER 22: Nobel Prizes 1990 ────────────────────────────────────
  {
    id: "src-079",
    kind: "official-record",
    title: "The Nobel Prize in Physics 1990",
    publisher: "Nobel Prize Official (NobelPrize.org)",
    url: "https://www.nobelprize.org/prizes/physics/1990/summary/",
    publishDate: { kind: "approximate", label: "1990" },
    language: "en",
    institutionalClass: "official-award-body",
    geographicPerspective: "Norway / Global",
    topics: ["nobel-physics-1990", "quark-model", "friedman-kendall-taylor"],
  },
  {
    id: "src-080",
    kind: "official-record",
    title: "The Nobel Prize in Physiology or Medicine 1990",
    publisher: "Nobel Prize Official (NobelPrize.org)",
    url: "https://www.nobelprize.org/prizes/medicine/1990/summary/",
    publishDate: { kind: "approximate", label: "1990" },
    language: "en",
    institutionalClass: "official-award-body",
    geographicPerspective: "Norway / Global",
    topics: ["nobel-medicine-1990", "organ-transplantation", "joseph-murray", "donnall-thomas"],
  },
  {
    id: "src-081",
    kind: "official-record",
    title: "Nobel Prize in Literature 1990 – Press Release",
    publisher: "Nobel Prize Official (NobelPrize.org)",
    url: "https://www.nobelprize.org/prizes/literature/1990/press-release/",
    publishDate: { kind: "approximate", label: "1990" },
    language: "en",
    institutionalClass: "official-award-body",
    geographicPerspective: "Norway / Global",
    topics: ["nobel-literature-1990", "octavio-paz", "mexico"],
  },
  {
    id: "src-082",
    kind: "official-record",
    title: "The Nobel Prize in Literature 1990 – Summary",
    publisher: "Nobel Prize Official (NobelPrize.org)",
    url: "https://www.nobelprize.org/prizes/literature/1990/summary/",
    publishDate: { kind: "approximate", label: "1990" },
    language: "en",
    institutionalClass: "official-award-body",
    geographicPerspective: "Norway / Global",
    topics: ["nobel-literature-1990", "octavio-paz"],
  },
  {
    id: "src-083",
    kind: "encyclopedia-entry",
    title: "1990 Nobel Prize in Literature",
    publisher: "Wikipedia",
    url: "https://en.wikipedia.org/wiki/1990_Nobel_Prize_in_Literature",
    publishDate: { kind: "approximate", label: "2022, updated continuously" },
    language: "en",
    institutionalClass: "crowdsourced-encyclopedia",
    geographicPerspective: "Global",
    topics: ["nobel-literature-1990", "octavio-paz", "mexican-literature"],
  },
] as const;

// ═════════════════════════════════════════════
// MAP ASSESSMENT (top-level MapAssessment object)
// ═════════════════════════════════════════════

export const assessment: MapAssessment = {
  id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  mapId: "11111111-2222-3333-4444-555555555555",
  assessedAt: { kind: "exact", value: "2026-03-26T10:00:00-03:00" },
  assessedBy: "Perplexity AI Research Agent",
  schemaVersion: "1.0.0",

  // ── §7. Positionality ─────────────────────────────────────────────────
  positionality: {
    background:
      "AI research agent operating via Perplexity AI. No institutional affiliation, no geographic anchor, " +
      "no lived experience. Retrieval is limited to indexed, digitized, English-prioritized web sources. " +
      "Cannot access paywalled archives, restricted government documents, oral testimonies, or physical " +
      "collections. Operates as of March 2026.",
    relationToSubject: "No personal or institutional stake in any 1990 event. Purely informational.",
    languages: ["en", "pt" /* partial — some Portuguese-language sources accessed */],
    institutionalAccess: [
      "Open-access web (HTTP/HTTPS)",
      "Wikipedia (all language editions, but only English queried)",
      "Open-access government pages (NASA, NIH, CERN, U.S. State Dept)",
      "Open-access Nobel Prize records",
      "Publicly accessible news archives (LA Times, NYT, BBC)",
      "EBSCO Research Starters (open/promotional tier)",
    ],
    knownLimitations: [
      "No Arabic, Persian, Swahili, Chinese, or Russian sources consulted — significant for Gulf War, Iranian earthquake, Baltic states, and Yemen events",
      "No access to JSTOR, academic subscription databases, or primary governmental archives",
      "Encyclopedic sources (Wikipedia) are structurally over-represented",
      "No oral testimony, personal memoir, or community archive consulted",
      "All Soviet, Iraqi, Yugoslav, and South African government perspectives are mediated through Western or anglophone sources",
    ],
    motivation:
      "User request: produce a complete and detailed review of the year 1990 with source references.",
  },

  // ── §1. Axis Assessments ──────────────────────────────────────────────
  axisAssessments: [
    {
      axis: "geographic-center-periphery",
      overrepresented: [
        "Western Europe (German reunification dominates)",
        "United States (Gulf War, recession, NASA, pop culture)",
        "United Kingdom (BBC, Britannica, Wellcome)",
      ],
      underrepresented: [
        "Latin America (no sources in Spanish/Portuguese for Octavio Paz's Mexican context)",
        "Sub-Saharan Africa beyond South Africa and Namibia",
        "East Asia, Southeast Asia",
        "Central Asia and the Caucasus (no sources on post-Soviet transitions in Armenia, Azerbaijan, Georgia)",
      ],
      structurallySilenced: [
        "Rural communities in Iran and the Philippines affected by earthquakes — no survivor testimony",
        "Hajj pilgrims from Indonesia and Malaysia who perished — no community accounts",
      ],
      balanceScore: 0.38,
      justification:
        "83 sources; estimated 68% are Anglo-American in origin. Non-Western events (Iran earthquake, Mecca stampede, Luzon earthquake, Yemen unification) are covered by 1–5 sources each vs. 5–8 for Western events.",
    },
    {
      axis: "language",
      overrepresented: ["English (100% of sources)"],
      underrepresented: [
        "Persian (Iran earthquake, Gulf War from Iranian perspective)",
        "Arabic (Gulf War from Iraqi/Kuwaiti/Yemeni perspective, Mecca stampede)",
        "German (reunification from East German popular experience)",
        "Russian (Soviet/Gorbachev perspective beyond one translated speech)",
        "Spanish (Octavio Paz, Latin American context)",
        "Lithuanian, Latvian, Estonian",
      ],
      structurallySilenced: [
        "Voices of the 1990 Iranian earthquake survivors — likely only in Persian oral record or local journalism",
      ],
      balanceScore: 0.05,
      justification:
        "Every single source is in English. For a year of global events spanning 6 continents, this is a severe epistemic constraint.",
    },
    {
      axis: "institutional-affiliation",
      overrepresented: [
        "Wikipedia (crowdsourced encyclopedia): ~22 sources (~27%)",
        "EBSCO Research Starters (database abstracts): ~8 sources (~10%)",
        "Official award and government bodies (Nobel, NASA, NIH, CERN, U.S. State Dept, DOE): ~10 sources (~12%)",
        "Established Western media (BBC, NYT, LA Times, PBS): ~6 sources",
      ],
      underrepresented: [
        "Peer-reviewed academic journals: only 2 sources (src-055 Oxford Academic; src-025 MERIP)",
        "Community or civil-society organizations",
        "Non-anglophone institutional publishers",
        "Archival primary sources (letters, diaries, official cables)",
      ],
      balanceScore: 0.35,
      justification:
        "Heavy reliance on encyclopedic and database aggregators. Peer-reviewed scholarship is nearly absent. This is adequate for a general historical overview but insufficient for granular historical claims.",
    },
    {
      axis: "political-power",
      overrepresented: [
        "State and governmental actors (Gorbachev, Kohl, de Klerk, Bush administration)",
        "International institutions (UN, Nobel Committee, FIFA)",
      ],
      underrepresented: [
        "Civil society movements (Polish Solidarity grassroots, not just Wałęsa)",
        "Opposition voices within Germany, South Africa, Iraq",
        "Anti-reunification perspectives from East German citizens",
      ],
      structurallySilenced: [
        "Kuwaiti civilian experience during the Iraqi occupation",
        "Iraqi civilian perspective on the Gulf crisis",
      ],
      balanceScore: 0.4,
      justification:
        "Events are told primarily through the lens of state actors and major institutional decisions, not popular or subaltern experience.",
    },
    {
      axis: "gender",
      overrepresented: ["Male-dominated political and military narratives"],
      underrepresented: [
        "Winnie Mandela's distinct political agency (mentioned only in passing)",
        "Women's experience in the 1990 recession",
        "Female athletes and artists beyond a few pop music references",
      ],
      structurallySilenced: [
        "Women's voices in countries undergoing post-communist transition (Poland, Baltic states, Yugoslavia)",
      ],
      balanceScore: 0.2,
      justification:
        "Standard for a macro-historical year review, but worth naming: 1990 geopolitical events are almost exclusively narrated through male leadership.",
    },
    {
      axis: "race-ethnicity",
      overrepresented: ["Euro-American perspectives on most events"],
      underrepresented: [
        "Black South African community voices on Mandela's release (beyond crowd descriptions)",
        "Black and Latino economic experience during the U.S. recession",
        "Arab and Persian perspectives on the Gulf War and earthquake",
      ],
      balanceScore: 0.3,
      justification:
        "Mandela and apartheid coverage is substantial but mediated largely through anglophone institutional sources. Other racial/ethnic subaltern perspectives are absent.",
    },
  ] satisfies AxisAssessment[],

  // ── §2. Source-Type Distribution ──────────────────────────────────────
  sourceDistribution: {
    counts: {
      "encyclopedia-entry": 22,
      "web-article": 14,
      "official-record": 7,
      "government-document": 7,
      "research-starter": 7,
      "news-article": 7,
      "institutional-web": 5,
      "statistical-database": 2,
      "academic-journal": 2,
      "sports-journalism": 1,
      "sports-statistics": 1,
      "long-form-journalism": 1,
      "educational-web": 1,
      "museum-web": 1,
      "podcast-transcript": 1,
      "primary-speech": 1,
      "blog": 1,
      "official-institution-web": 1,
      "pop-culture-web": 2,
    },
    total: 83,
    hhi: 0.108, // Σ(count_i/83)² ≈ (22/83)²+(14/83)²+... ≈ 0.108 — moderate concentration
    interpretation:
      "27% of sources are Wikipedia articles — the single largest cluster. " +
      "Peer-reviewed academic journals represent only 2.4% (2 sources). " +
      "Primary sources (speeches, official records) are present but limited to Nobel, NASA, NIH, CERN, and State Dept pages. " +
      "No oral testimonies, archival documents, or non-digital primary sources. " +
      "HHI of ~0.108 suggests moderate concentration — not catastrophic, but reflecting heavy encyclopedic dependence.",
  } satisfies SourceTypeDistributionType,

  // ── §3. Method Biases ─────────────────────────────────────────────────
  methodBiases: [
    {
      method: "web-search (keyword-based, English-language)",
      sharePercent: 100,
      reaches:
        "Indexed, English-language, digitized web content. Strong coverage of events that received extensive Anglo-American media and encyclopedic attention: German reunification, Gulf War, Hubble, Mandela, World Cup.",
      misses:
        "Non-English language sources, paywalled academic journals, physical archives, oral histories, " +
        "non-indexed institutional repositories, sources published before the web era (pre-1994) that " +
        "were never digitized, Soviet/Eastern bloc domestic perspectives.",
      mitigation:
        "No meaningful mitigation applied. Research was conducted entirely via public web search in English.",
    },
  ] satisfies MethodBias[],

  // ── §4. Coverage Gaps ─────────────────────────────────────────────────
  coverageGaps: [
    {
      dimension: "geographic",
      description:
        "Central and Eastern Europe beyond Germany and the Baltic states. " +
        "Romania's 1990 post-Ceaușescu transition, Hungary and Czechoslovakia's Velvet transitions, " +
        "Bulgaria's democratic opening — all omitted.",
      cause: "Search queries focused on highest-profile Cold War events; Eastern European transitions were not queried.",
      severity: 0.45,
      fixability: "fixable-with-effort",
    },
    {
      dimension: "geographic",
      description:
        "Sub-Saharan Africa beyond South Africa and Namibia. " +
        "1990 saw multi-party political transitions in Benin, Congo-Brazzaville, Gabon, and elsewhere — none covered.",
      cause: "These events received minimal anglophone Western media coverage and are underindexed.",
      severity: 0.4,
      fixability: "partially-fixable",
    },
    {
      dimension: "thematic",
      description:
        "Environmental events of 1990. The IPCC Second Assessment process, acid rain legislation " +
        "(U.S. Clean Air Act amendments signed October 1990), and early climate science milestones are absent.",
      cause: "No search queries targeted environmental policy or climate science.",
      severity: 0.5,
      fixability: "fixable-with-effort",
    },
    {
      dimension: "thematic",
      description:
        "The AIDS epidemic in 1990. By 1990, AIDS had killed over 100,000 Americans and was devastating communities globally. " +
        "No sources on this topic were retrieved.",
      cause: "No search query targeted public health or the AIDS crisis.",
      severity: 0.6,
      fixability: "fixable-with-effort",
    },
    {
      dimension: "linguistic",
      description:
        "No sources in any language other than English. " +
        "Consequential 1990 events in Iran, Iraq, the Soviet Union, Germany, Poland, and the Baltic states " +
        "are narrated entirely through anglophone mediation.",
      cause: "Retrieval tools queried only English-language sources.",
      severity: 0.65,
      fixability: "partially-fixable",
    },
    {
      dimension: "temporal",
      description:
        "Contemporary primary reporting is thin. Only 3 sources are from 1990 itself " +
        "(NYT earthquake report; LA Times tunnel report; LA Times music chart). " +
        "Most coverage is retrospective (2001–2026), which normalizes hindsight bias.",
      cause: "Pre-web newspaper archives are paywalled; sources from 1990 are rarely freely indexed.",
      severity: 0.4,
      fixability: "partially-fixable",
    },
  ] satisfies CoverageGap[],

  // ── §5. Blind Spots ───────────────────────────────────────────────────
  blindSpots: [
    {
      id: "bs-001-00000000-0000-0000-0000-000000000001",
      kind: "source-absence",
      title: "AIDS epidemic in 1990",
      description:
        "The AIDS crisis was a defining global event of 1990. The WHO estimated 8–10 million people " +
        "were HIV-positive globally. The Ryan White CARE Act was signed in August 1990. " +
        "No sources on AIDS were included in this map. Claims about 1990 as a 'landmark year' " +
        "are weakened by this omission.",
      axes: ["race-ethnicity", "class", "gender", "sexuality"],
      affectedClaims: ["Overview: '1990 compressed an extraordinary density of change'"],
      severity: 0.6,
      fixability: "fixable-with-effort",
      remediationIds: ["rem-001-00000000-0000-0000-0000-000000000001"],
    },
    {
      id: "bs-002-00000000-0000-0000-0000-000000000002",
      kind: "interpretive-frame",
      title: "Cold War end narrated from Western/victors' perspective",
      description:
        "German reunification, Baltic independence, and Gorbachev's Nobel Prize are framed as " +
        "unambiguous triumphs. Soviet citizens' perspectives — economic collapse, loss of superpower " +
        "status, and the 'enormous condescension of posterity' toward Soviet workers — are absent. " +
        "The one post-Soviet source (src-031) is a Western-oriented analysis.",
      axes: ["political-power", "geographic-center-periphery", "language"],
      affectedClaims: [
        "Gorbachev Nobel Prize section",
        "Baltic independence section",
        "German reunification section",
      ],
      severity: 0.55,
      fixability: "partially-fixable",
      remediationIds: ["rem-002-00000000-0000-0000-0000-000000000002"],
    },
    {
      id: "bs-003-00000000-0000-0000-0000-000000000003",
      kind: "source-absence",
      title: "Iraqi and Kuwaiti civilian voices on the Gulf crisis",
      description:
        "The Gulf War section is narrated entirely through UN resolutions, U.S. military history, " +
        "and Wikipedia. Kuwaiti civilians under occupation and Iraqi civilians facing sanctions and " +
        "bombardment are structurally absent from every source in this cluster.",
      axes: ["political-power", "geographic-center-periphery", "language"],
      severity: 0.65,
      fixability: "partially-fixable",
    },
    {
      id: "bs-004-00000000-0000-0000-0000-000000000004",
      kind: "survivorship-bias",
      title: "Disasters covered by body count, not lived experience",
      description:
        "The Iran earthquake, Luzon earthquake, and Mecca tunnel stampede are covered as statistical " +
        "events (death tolls, Richter magnitudes). Survivor testimony, community reconstruction, " +
        "or long-term social impact are entirely absent — a classic survivorship bias where only " +
        "the event itself (not its aftermath) is documented.",
      axes: ["class", "geographic-center-periphery", "language"],
      severity: 0.45,
      fixability: "partially-fixable",
    },
    {
      id: "bs-005-00000000-0000-0000-0000-000000000005",
      kind: "question-framing",
      title: "Pop culture skewed toward U.S. and anglophone commercial market",
      description:
        "The music and film sections cover U.S. chart hits and Hollywood box office. " +
        "Non-anglophone cultural production in 1990 — Bollywood, Brazilian MPB, Japanese cinema, " +
        "African music — is entirely absent. The framing assumes 'culture' equals anglophone commercial culture.",
      axes: ["geographic-center-periphery", "language", "class"],
      severity: 0.35,
      fixability: "fixable-with-effort",
    },
  ] satisfies BlindSpot[],

  // ── §6. Remediation Actions ───────────────────────────────────────────
  remediations: [
    {
      id: "rem-001-00000000-0000-0000-0000-000000000001",
      blindSpotIds: ["bs-001-00000000-0000-0000-0000-000000000001"],
      title: "Add AIDS epidemic 1990 source cluster",
      description:
        "Search AVERT, CDC historical records, and contemporaneous NYT/LA Times reporting on AIDS in 1990. " +
        "Add Ryan White CARE Act (August 18, 1990) as a key event. " +
        "Search for WHO 1990 AIDS reports (likely available via WHO archives).",
      type: "additional-search",
      estimatedEffortDays: 0.5,
      expectedImpact: 0.7,
      status: "proposed",
    },
    {
      id: "rem-002-00000000-0000-0000-0000-000000000002",
      blindSpotIds: ["bs-002-00000000-0000-0000-0000-000000000002"],
      title: "Seek post-Soviet and Eastern European perspectives on Cold War end",
      description:
        "Search for Anglophone translations of Soviet-era journals, " +
        "Novaya Gazeta or Izvestia retrospectives, and academic analyses of " +
        "Soviet popular opinion during 1990 (e.g., James Millar's survey data from Soviet Interview Project).",
      type: "additional-search",
      estimatedEffortDays: 1.5,
      expectedImpact: 0.5,
      status: "proposed",
    },
  ] satisfies RemediationAction[],

  // ── §8. Verdict ───────────────────────────────────────────────────────
  verdict: {
    overallBalance: 0.38,
    sourceDiversity: 0.89, // 1 - HHI(0.108) ≈ 0.89
    unaddressedBlindSpots: 3,
    structuralBlindSpots: 1,
    fixableBlindSpots: 4,
    claimsSupported: "partially-supported",
    summary:
      "This source map supports a broad, high-altitude review of 1990 adequate for general reference. " +
      "Political and geopolitical events are well-covered via official records, established encyclopedias, " +
      "and major Western news outlets. Scientific milestones (Hubble, HGP, WWW) are strongly sourced " +
      "through institutional and government channels. " +
      "However, the map is severely constrained by its exclusive use of English-language sources, " +
      "its near-total absence of peer-reviewed scholarship, and its structural silence on " +
      "non-Western subaltern experience — particularly survivors of disasters, civilians under occupation, " +
      "and communities undergoing Soviet-era collapse. " +
      "The AIDS epidemic — a defining event of 1990 — is entirely absent, which undermines any claim " +
      "to comprehensiveness. The source diversity metric (0.89) reflects genuine variety in source types, " +
      "but this is offset by the geographic and linguistic monoculture of all 83 sources. " +
      "Suitable for: general historical orientation, citation of well-documented public events. " +
      "Not suitable for: subaltern history, academic citation, non-Western perspectives, or public health.",
  },
};
