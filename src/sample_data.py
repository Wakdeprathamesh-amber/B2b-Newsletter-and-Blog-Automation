"""Sample/mock data for dev mode testing.

When dev_mode=True and no API key is set, the pipeline uses this data
instead of real scraping + LLM calls. This lets you run and test the
full pipeline end-to-end locally.

Volumes match production targets:
  - Signals: 10-15 per region (60+ total)
  - Ranked topics: 30-50 (8-12 per region)
  - Shortlisted topics: 7-12 per region (35-55 total)
"""

from datetime import datetime, timedelta, timezone

from src.models.enums import (
    DraftChannel,
    DraftStatus,
    DraftVoice,
    Region,
    StakeholderAudience,
    TopicCategory,
    UrgencyLevel,
)
from src.models.schemas import ContentDraft, Signal, Topic


def _days_ago(n: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=n)


# ── Signals: 10-15 per region ─────────────────────────────────────────────

def get_sample_signals(cycle_id: str) -> list[Signal]:
    """Return 60+ realistic sample signals (10-15 per region)."""
    signals = []
    signals.extend(_uk_signals(cycle_id))
    signals.extend(_usa_signals(cycle_id))
    signals.extend(_au_signals(cycle_id))
    signals.extend(_eu_signals(cycle_id))
    signals.extend(_global_signals(cycle_id))
    # Re-number signal IDs sequentially
    for i, s in enumerate(signals, 1):
        s.signal_id = f"sig-{i:03d}"
    return signals


def _uk_signals(cycle_id: str) -> list[Signal]:
    return [
        Signal(
            signal_id="", source_name="HESA",
            source_url="https://www.hesa.ac.uk/news/2026/student-numbers",
            headline="International student enrolments rise 4.2% in 2025-26",
            summary="UK international student numbers rose 4.2% year-on-year to 758,000, according to HESA's latest release. Nigerian enrolments surged 31% and Indian students grew 12%, while Chinese numbers fell 8% for the third consecutive year. For PBSA operators, the shift in nationality mix changes demand patterns in key university cities — Nigerian and Indian students typically prefer shared flats over studios. Universities relying on Chinese fee income face a widening revenue gap that diversified recruitment can partially address.",
            published_date=_days_ago(5), region=Region.UK,
            topic_category=TopicCategory.STUDENT_DEMAND,
            raw_content="Full HESA release text...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Knight Frank",
            source_url="https://www.knightfrank.co.uk/research/uk-pbsa-2026",
            headline="UK PBSA rents rise 6.8% as supply lags demand",
            summary="Average UK PBSA rents increased 6.8% nationally in 2025-26, with Russell Group cities seeing 8-9% growth, per Knight Frank's annual report. New supply delivery fell 15% short of pipeline targets due to planning delays and construction cost inflation. The supply-demand imbalance is most acute in Bristol, Edinburgh, and Manchester where vacancy rates sit below 1%. Operators with existing stock in these cities are positioned for continued rental growth into 2027.",
            published_date=_days_ago(8), region=Region.UK,
            topic_category=TopicCategory.RENT_TRENDS,
            raw_content="Full Knight Frank report...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Home Office",
            source_url="https://www.gov.uk/government/statistics/immigration-q1-2026",
            headline="Student visa grants fall 12% in Q1 2026",
            summary="Home Office data reveals a 12% drop in student visa grants for Q1 2026 vs the same period last year, with 89,400 grants vs 101,600 in Q1 2025. The decline is driven by stricter Graduate Route eligibility (dependant ban) and a £2,800 increase in financial requirements. Indian applicants fell 18% while Nigerian applicants dropped 9%. The next data release in July will show whether the decline is stabilising or accelerating — operators should model both scenarios for 2026-27 occupancy planning.",
            published_date=_days_ago(3), region=Region.UK,
            topic_category=TopicCategory.VISA_DATA,
            raw_content="Full Home Office statistical release...", cycle_id=cycle_id,
            is_negative_news=True,
        ),
        Signal(
            signal_id="", source_name="StuRents",
            source_url="https://www.sturents.com/data/rent-index-march-2026",
            headline="Student rent index shows 5.1% annual growth",
            summary="StuRents' March 2026 index shows average student rents grew 5.1% year-on-year across the UK, but with sharp regional divergence. London rents plateaued at +0.8% as affordability limits bite, while Manchester (+7.4%), Leeds (+7.8%), and Birmingham (+6.2%) led growth. The north-south gap in student rent inflation is now the widest since StuRents began tracking in 2018. For operators, northern cities offer both stronger yield growth and lower entry prices per bed.",
            published_date=_days_ago(7), region=Region.UK,
            topic_category=TopicCategory.RENT_TRENDS,
            raw_content="Full StuRents index...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="The PIE News",
            source_url="https://thepienews.com/analysis/uk-policy-impact-2026",
            headline="UK graduate visa changes push students toward Australia and Canada",
            summary="Education agents report a 15% increase in enquiries for Australian and Canadian institutions since the UK Graduate Route reforms took effect in January 2026, per PIE News analysis of 40 agencies across 8 countries. The UK's share of first-preference applications from Indian students fell from 34% to 28% in the same period. Agents cite the dependant visa ban and higher financial thresholds as the top two deterrents. The UK risks losing ground to competitors unless policy messaging improves.",
            published_date=_days_ago(4), region=Region.UK,
            topic_category=TopicCategory.POLICY_CHANGES,
            raw_content="Full PIE News article...", cycle_id=cycle_id,
            is_negative_news=True, is_opinion=True,
        ),
        Signal(
            signal_id="", source_name="UCAS",
            source_url="https://www.ucas.com/data-and-analysis/applicant-data-2026",
            headline="UCAS reports record international applications for 2026 entry",
            summary="International applications for September 2026 UK entry rose 6% to a record 145,000, per UCAS data. Sub-Saharan African applications surged 23% (led by Nigeria +28% and Ghana +19%), while Chinese applications fell 5% and Indian applications grew 3%. The diversification of the applicant pool has implications for accommodation preferences and price sensitivity — African students typically have lower budgets and prefer shared options. Universities need to expand their bursary and accommodation partnership offerings accordingly.",
            published_date=_days_ago(9), region=Region.UK,
            topic_category=TopicCategory.STUDENT_DEMAND,
            raw_content="Full UCAS statistics release...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Property Week",
            source_url="https://www.propertyweek.com/news/pbsa-planning-approvals-2026",
            headline="UK PBSA planning approvals fall to five-year low",
            summary="Just 12,400 new PBSA beds received planning approval in the 12 months to March 2026, a 32% drop from the prior year and the lowest since 2021, per Property Week analysis of Glenigan data. London and the South East account for 48% of stalled applications, with local authority objections citing density and infrastructure concerns. The planning bottleneck will widen the supply gap further — operators with approved sites hold a significant competitive advantage through 2028-29.",
            published_date=_days_ago(6), region=Region.UK,
            topic_category=TopicCategory.SUPPLY_OUTLOOK,
            raw_content="Full Property Week article...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Unipol",
            source_url="https://www.unipol.org.uk/research/affordability-report-2026",
            headline="Unipol: 38% of students spend over 60% of loan on rent",
            summary="Unipol's 2026 affordability report reveals 38% of UK students now spend more than 60% of their maintenance loan on rent, up from 31% two years ago. The average student rent-to-loan ratio has risen to 72% in London and 58% nationally. Unipol recommends a £500 minimum maintenance loan increase. For PBSA operators, this raises regulatory and reputational risk if rent increases continue outpacing student funding — universities may push back on partnership rents.",
            published_date=_days_ago(11), region=Region.UK,
            topic_category=TopicCategory.RENT_TRENDS,
            raw_content="Full Unipol report...", cycle_id=cycle_id,
            is_negative_news=True,
        ),
        Signal(
            signal_id="", source_name="MAC",
            source_url="https://www.gov.uk/government/publications/mac-annual-report-2026",
            headline="MAC recommends maintaining Graduate Route with monitoring",
            summary="The Migration Advisory Committee's 2026 annual report recommends keeping the Graduate Route but with enhanced labour market tracking of graduate outcomes. The MAC found 67% of Graduate Route holders are in skilled employment 18 months after graduation, above the 60% threshold that triggered the review. The recommendation reduces the risk of further policy tightening in the near term. Universities and agents can use this as a positive recruitment message for the 2027 intake cycle.",
            published_date=_days_ago(2), region=Region.UK,
            topic_category=TopicCategory.POLICY_CHANGES,
            raw_content="Full MAC report...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Savills",
            source_url="https://www.savills.co.uk/research/student-accommodation-2026",
            headline="UK PBSA yields compress to 5.0% for prime assets",
            summary="Prime UK PBSA yields compressed 25 basis points to 5.0% in Q1 2026, the tightest since 2019, per Savills' quarterly tracker. Regional city yields sit at 5.5-6.0%, with the strongest investor appetite in Manchester, Birmingham, and Bristol. Transaction volumes reached £1.8bn in Q1, up 40% year-on-year. Savills notes overseas investors (particularly Middle Eastern and Asian sovereign funds) drove 62% of deals — a signal that PBSA is firmly established as an institutional asset class.",
            published_date=_days_ago(10), region=Region.UK,
            topic_category=TopicCategory.SUPPLY_OUTLOOK,
            raw_content="Full Savills research...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="ICEF Monitor",
            source_url="https://monitor.icef.com/2026/uk-russell-group-intl-growth",
            headline="Russell Group international intake grows 8% despite visa headwinds",
            summary="Russell Group universities collectively grew their international intake by 8% in 2025-26 despite the broader 12% visa decline, per ICEF Monitor analysis. The top 24 universities captured a larger share of a shrinking visa pool, with non-Russell Group institutions bearing the brunt of the drop (-19%). This concentration trend accelerates demand for PBSA in Russell Group cities while creating vacancy risk in mid-tier university towns. Operators should reassess portfolio exposure to non-Russell Group locations.",
            published_date=_days_ago(8), region=Region.UK,
            topic_category=TopicCategory.STUDENT_DEMAND,
            raw_content="Full ICEF analysis...", cycle_id=cycle_id,
            is_opinion=True,
        ),
        Signal(
            signal_id="", source_name="The Guardian",
            source_url="https://www.theguardian.com/education/2026/uk-university-finances",
            headline="Five UK universities in financial distress, warns OfS",
            summary="The Office for Students has issued enhanced financial monitoring notices to five UK universities facing 'material financial uncertainty', with combined deficits of £380m. Three of the five are in northern England with significant international student populations. OfS projects up to 12 institutions could require financial restructuring by 2028 if international recruitment declines continue. For PBSA operators, university financial health directly impacts nomination agreements and guaranteed occupancy — operators should stress-test their exposure to at-risk institutions.",
            published_date=_days_ago(1), region=Region.UK,
            topic_category=TopicCategory.POLICY_CHANGES,
            raw_content="Full Guardian article...", cycle_id=cycle_id,
            is_negative_news=True,
        ),
    ]


def _usa_signals(cycle_id: str) -> list[Signal]:
    return [
        Signal(
            signal_id="", source_name="IIE",
            source_url="https://www.iie.org/research/open-doors-2026",
            headline="US hosts record 1.2 million international students",
            summary="US international student numbers reached a record 1.2 million in 2025-26, a 7% increase year-on-year, per IIE's Open Doors report. Indian students (335,000) overtook Chinese (290,000) as the largest cohort for the first time, growing 24% vs China's 9% decline. STEM programmes account for 56% of all international enrolments. For US PBSA operators, the shift toward Indian students implies higher demand for value-priced shared accommodation near large public universities rather than premium studios.",
            published_date=_days_ago(12), region=Region.USA,
            topic_category=TopicCategory.STUDENT_DEMAND,
            raw_content="Full Open Doors report...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="NMHC",
            source_url="https://www.nmhc.org/research/student-housing-outlook-2026",
            headline="US student housing occupancy hits 96.2% nationwide",
            summary="The National Multifamily Housing Council reports US purpose-built student housing occupancy reached 96.2% for Fall 2025, the highest in a decade. Pre-leasing velocity is running 8 percentage points ahead of the same period last year. Average rents grew 4.8% nationally, with the highest growth in Sun Belt university cities (6-8%). Supply additions remain concentrated in the top 50 university markets, leaving mid-tier schools underserved.",
            published_date=_days_ago(9), region=Region.USA,
            topic_category=TopicCategory.RENT_TRENDS,
            raw_content="Full NMHC report...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="SEVP",
            source_url="https://studyinthestates.dhs.gov/sevis-data-2026",
            headline="SEVIS data shows 9% rise in active F-1 student records",
            summary="SEVP's quarterly SEVIS report shows 1.35 million active F-1 student records as of March 2026, up 9% from March 2025. New initial student records (first-time enrolments) rose 11%, indicating strong pipeline momentum. Computer science and engineering programmes drive 42% of new records. Texas, California, and New York remain the top three host states, but North Carolina and Georgia posted the fastest growth (+18% and +15% respectively).",
            published_date=_days_ago(5), region=Region.USA,
            topic_category=TopicCategory.STUDENT_DEMAND,
            raw_content="Full SEVP release...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="RealPage",
            source_url="https://www.realpage.com/analytics/student-housing-spring-2026",
            headline="US student housing investment volume hits $12.8bn in 2025",
            summary="Annual US student housing transaction volume reached $12.8 billion in 2025, surpassing the 2022 record of $11.2bn, per RealPage analytics. Cap rates compressed to 4.8% for core assets in Power 5 conference markets. International investors comprised 28% of buyers, up from 19% in 2024. The data confirms student housing is now competing with conventional multifamily for institutional capital — operators should expect more sophisticated competition.",
            published_date=_days_ago(14), region=Region.USA,
            topic_category=TopicCategory.SUPPLY_OUTLOOK,
            raw_content="Full RealPage analysis...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Inside Higher Ed",
            source_url="https://www.insidehighered.com/news/2026/opt-stem-extensions",
            headline="OPT STEM extension proposal could boost US attractiveness",
            summary="A bipartisan bill introduced in the US Senate proposes extending Optional Practical Training (OPT) for STEM graduates from 36 to 48 months, which would add an estimated 85,000 student-years of US residency annually. The bill has support from 30 major universities and the tech industry lobby. If passed, this would significantly boost the US's competitiveness vs the UK and Australia for Indian and Chinese STEM students. Education agents should monitor the bill's progress through the Senate Commerce Committee.",
            published_date=_days_ago(3), region=Region.USA,
            topic_category=TopicCategory.POLICY_CHANGES,
            raw_content="Full IHE article...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="The Chronicle",
            source_url="https://www.chronicle.com/article/us-housing-crisis-international-2026",
            headline="US campus housing shortages hit international students hardest",
            summary="A Chronicle of Higher Education survey of 200 universities finds 73% report insufficient on-campus housing for international students, up from 58% in 2023. International students face 2.3x higher off-campus rent burdens than domestic peers on average. 42% of surveyed institutions now partner with private PBSA operators for guaranteed bed allocations. The housing gap creates a direct market opportunity for operators willing to structure university partnership deals with international student-specific amenities.",
            published_date=_days_ago(7), region=Region.USA,
            topic_category=TopicCategory.SUPPLY_OUTLOOK,
            raw_content="Full Chronicle article...", cycle_id=cycle_id,
            is_opinion=True,
        ),
        Signal(
            signal_id="", source_name="ICEF Monitor",
            source_url="https://monitor.icef.com/2026/us-community-college-international",
            headline="US community colleges see 22% surge in international enrolments",
            summary="International enrolments at US community colleges jumped 22% in Fall 2025, the fastest growth in the higher education sector, per ICEF Monitor. Vietnamese and Filipino students drove the increase, seeking more affordable pathways. Average community college tuition ($9,400/year) is 72% cheaper than four-year institutions. For PBSA operators, community college markets represent an underserved niche — these students need affordable, well-located housing options near suburban campuses.",
            published_date=_days_ago(10), region=Region.USA,
            topic_category=TopicCategory.STUDENT_DEMAND,
            raw_content="Full ICEF article...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="JLL Americas",
            source_url="https://www.jll.com/en/research/us-student-housing-q1-2026",
            headline="US student housing development pipeline hits record 58,000 beds",
            summary="JLL reports 58,000 new student housing beds under construction across the US as of Q1 2026, a 15% increase from the prior year. Texas (9,200 beds), Florida (7,100), and North Carolina (4,800) lead new supply. Average development costs have risen 18% since 2023, pushing developers toward higher-rent markets to maintain returns. Delivery is concentrated in 2027-28, creating a potential short-term oversupply risk in Sun Belt university markets.",
            published_date=_days_ago(6), region=Region.USA,
            topic_category=TopicCategory.SUPPLY_OUTLOOK,
            raw_content="Full JLL report...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Forbes",
            source_url="https://www.forbes.com/advisor/education/us-visa-processing-delays-2026",
            headline="US student visa interview wait times fall to 14-day average",
            summary="Average US student visa (F-1) interview wait times dropped to 14 days globally in Q1 2026, down from 42 days in Q1 2024, per State Department data cited by Forbes. India (18 days) and Nigeria (21 days) remain above average but improved substantially from 60+ day waits two years ago. Faster processing removes a key friction point that had been redirecting students to the UK and Canada. Agents should factor improved US visa timelines into 2027 intake guidance.",
            published_date=_days_ago(4), region=Region.USA,
            topic_category=TopicCategory.VISA_DATA,
            raw_content="Full Forbes article...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="CBRE",
            source_url="https://www.cbre.com/insights/us-student-housing-spring-2026",
            headline="US student housing rent growth moderating to 4.2% in Spring 2026",
            summary="CBRE's Spring 2026 student housing report shows rent growth decelerating to 4.2% year-on-year from 6.1% in Spring 2025, as new supply begins to absorb excess demand. Luxury/amenity-rich properties maintained 5.5% growth while value-tier assets slowed to 2.8%. Occupancy remains healthy at 95.8% but pre-leasing velocity has slowed 3 percentage points. The moderation signals a maturing market — operators should focus on retention and value-add renovations rather than aggressive rent increases.",
            published_date=_days_ago(8), region=Region.USA,
            topic_category=TopicCategory.RENT_TRENDS,
            raw_content="Full CBRE report...", cycle_id=cycle_id,
            is_opinion=True,
        ),
    ]


def _au_signals(cycle_id: str) -> list[Signal]:
    return [
        Signal(
            signal_id="", source_name="DHA",
            source_url="https://www.homeaffairs.gov.au/research/student-visa-statistics",
            headline="Australia tightens student visa processing amid housing pressure",
            summary="The Department of Home Affairs extended student visa processing times from 4-6 weeks to 8-12 weeks, citing accommodation capacity constraints in Sydney, Melbourne, and Brisbane. Visa grant rates fell 6 percentage points to 82% as additional Genuine Student Test scrutiny was applied. The policy directly links housing availability to visa processing for the first time. Quality PBSA operators with spare capacity can leverage this by providing accommodation guarantees that strengthen visa applications.",
            published_date=_days_ago(6), region=Region.AUSTRALIA,
            topic_category=TopicCategory.VISA_DATA,
            raw_content="Full DHA announcement...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Knight Frank AU",
            source_url="https://www.knightfrank.com.au/research/au-pbsa-market-2026",
            headline="Australian PBSA rents jump 9.3% as vacancy hits record low",
            summary="Australian PBSA rents rose 9.3% year-on-year in Q1 2026, the fastest growth globally, per Knight Frank. Vacancy rates hit a record low of 0.8% in Melbourne and 1.1% in Sydney. Average weekly rent reached AUD 485 for a studio and AUD 340 for a shared room. The 18,000-bed pipeline (2026-28) will address only 30% of the estimated shortage. Operators with existing Australian portfolios can expect sustained rent growth through at least 2028.",
            published_date=_days_ago(10), region=Region.AUSTRALIA,
            topic_category=TopicCategory.RENT_TRENDS,
            raw_content="Full Knight Frank AU report...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Australian Government",
            source_url="https://www.education.gov.au/international-education-data-2026",
            headline="Australia's international student cap set at 270,000 new enrolments",
            summary="The Australian Government confirmed a cap of 270,000 new international student enrolments for 2026, down from 295,000 in 2025 — a 8.5% reduction. The cap allocates quotas by institution tier: Group of Eight universities receive the largest share (35%), while private colleges face the sharpest cuts (-22%). For PBSA operators, the cap creates more predictable demand planning but also limits growth upside. Operators partnering with Go8 universities will be least affected.",
            published_date=_days_ago(4), region=Region.AUSTRALIA,
            topic_category=TopicCategory.POLICY_CHANGES,
            raw_content="Full government announcement...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="The Australian",
            source_url="https://www.theaustralian.com.au/higher-ed/student-housing-crisis-2026",
            headline="Student housing crisis: 42,000 bed shortfall projected by 2028",
            summary="A Deloitte report commissioned by Universities Australia projects a 42,000-bed shortfall in purpose-built student accommodation by 2028, even accounting for the new student cap. Melbourne (15,000 beds short), Sydney (12,000), and Brisbane (8,000) face the largest gaps. The report estimates AUD 8.4 billion in investment is needed to close the deficit. For operators, this quantifies the scale of the opportunity — Australia's PBSA market could double in the next five years if capital and planning approvals align.",
            published_date=_days_ago(8), region=Region.AUSTRALIA,
            topic_category=TopicCategory.SUPPLY_OUTLOOK,
            raw_content="Full article...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="SBS News",
            source_url="https://www.sbs.com.au/news/indian-students-australia-2026",
            headline="Indian students overtake Chinese as Australia's largest cohort",
            summary="Indian students now represent 27% of all international enrolments in Australia (189,000 students), surpassing Chinese students (24%, 168,000) for the first time, per DHA data. Indian student numbers grew 14% year-on-year while Chinese fell 6%. Indian students show stronger preference for Melbourne and Sydney over regional locations. The nationality shift has pricing implications — Indian students are more price-sensitive and prefer shared accommodation, creating demand for value-tier PBSA product.",
            published_date=_days_ago(5), region=Region.AUSTRALIA,
            topic_category=TopicCategory.STUDENT_DEMAND,
            raw_content="Full SBS article...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Savills AU",
            source_url="https://www.savills.com.au/research/pbsa-investment-au-2026",
            headline="Australian PBSA investment reaches AUD 3.1bn record",
            summary="Australian PBSA investment hit a record AUD 3.1 billion in 2025, up 35% from AUD 2.3bn in 2024, per Savills. Singaporean and Canadian pension funds led cross-border activity, comprising 58% of transactions. Melbourne captured 42% of investment volume, followed by Sydney (31%) and Brisbane (18%). Average transaction yield was 5.2%, tighter than UK equivalents. The data confirms Australia is the fastest-growing institutional PBSA market globally.",
            published_date=_days_ago(12), region=Region.AUSTRALIA,
            topic_category=TopicCategory.SUPPLY_OUTLOOK,
            raw_content="Full Savills report...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="ICEF Monitor",
            source_url="https://monitor.icef.com/2026/australia-vet-sector-international",
            headline="Australia's VET sector international enrolments surge 18%",
            summary="International enrolments in Australia's Vocational Education and Training (VET) sector grew 18% in 2025-26 to 210,000 students, outpacing the university sector (4% growth), per ICEF Monitor. Cookery, aged care, and IT courses drive demand, primarily from South Asian and Southeast Asian students. VET students represent an underserved segment for PBSA — they typically seek affordable, suburban accommodation near TAFE colleges rather than CBD or campus-adjacent product.",
            published_date=_days_ago(9), region=Region.AUSTRALIA,
            topic_category=TopicCategory.STUDENT_DEMAND,
            raw_content="Full ICEF article...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="ABC News",
            source_url="https://www.abc.net.au/news/2026/regional-australia-student-housing",
            headline="Regional Australian universities offer free accommodation to attract students",
            summary="Six regional Australian universities are now offering free or heavily subsidised accommodation for the first semester to attract international students away from overcrowded capital cities. The initiative covers 2,400 beds across campuses in Wollongong, Geelong, Townsville, and Newcastle. Take-up in Semester 1 2026 reached 78% of available beds. The trend signals a potential redistribution of demand away from Melbourne and Sydney that PBSA operators should monitor.",
            published_date=_days_ago(3), region=Region.AUSTRALIA,
            topic_category=TopicCategory.POLICY_CHANGES,
            raw_content="Full ABC article...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="The PIE News",
            source_url="https://thepienews.com/news/australia-agent-regulation-2026",
            headline="Australia introduces mandatory agent registration from July 2026",
            summary="The Australian Government will require all education agents recruiting for Australian institutions to register with a new national body from July 2026, with compliance audits and a public register. An estimated 4,500 agents globally will need to register. Non-compliant agents risk deregistration, which would block their students from visa processing. For HEA, this increases compliance costs but also professionalises the sector — amber-aligned agents who register early can differentiate themselves.",
            published_date=_days_ago(7), region=Region.AUSTRALIA,
            topic_category=TopicCategory.POLICY_CHANGES,
            raw_content="Full PIE News article...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Financial Review",
            source_url="https://www.afr.com/property/au-student-housing-build-to-rent-2026",
            headline="Build-to-rent developers pivot to student housing in Australia",
            summary="Three major Australian build-to-rent developers (Mirvac, Lendlease, Grocon) have announced pivots into purpose-built student housing, committing 8,500 beds across Melbourne and Sydney for delivery in 2028-29. The pivot is driven by stronger PBSA yields (5.2%) vs conventional BTR (4.4%) and more predictable demand cycles. Combined with existing PBSA specialists, the total Australian pipeline now exceeds 26,000 beds. Competition for sites near Group of Eight universities is intensifying.",
            published_date=_days_ago(2), region=Region.AUSTRALIA,
            topic_category=TopicCategory.SUPPLY_OUTLOOK,
            raw_content="Full AFR article...", cycle_id=cycle_id,
        ),
    ]


def _eu_signals(cycle_id: str) -> list[Signal]:
    return [
        Signal(
            signal_id="", source_name="JLL",
            source_url="https://www.jll.co.uk/en/research/european-pbsa-outlook",
            headline="European PBSA investment reaches EUR 4.2bn in 2025",
            summary="European PBSA investment volumes hit EUR 4.2 billion in 2025, a 22% increase year-on-year, per JLL. Germany (EUR 1.4bn) and the Netherlands (EUR 850m) led activity, while emerging interest in Poland (EUR 280m) and Portugal (EUR 190m) marked those markets' highest-ever volumes. Average European PBSA yields sit at 4.5-5.5%, making the sector attractive vs other real estate. The maturing European market now has a 15-country institutional investor base.",
            published_date=_days_ago(15), region=Region.EUROPE,
            topic_category=TopicCategory.SUPPLY_OUTLOOK,
            raw_content="Full JLL report...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="ICEF Monitor",
            source_url="https://monitor.icef.com/2026/emerging-corridors-africa",
            headline="African student mobility to Europe surges 18%",
            summary="African students choosing European destinations over traditional Anglophone markets grew 18% in 2025-26, per ICEF Monitor analysis of visa and enrolment data. France received the largest share (42,000 new African students, +14%), followed by Germany (28,000, +22%) and the Netherlands (15,000, +19%). Tuition-free or low-tuition programmes are the primary draw. The corridor shift creates PBSA demand in European cities that historically had limited purpose-built stock — Berlin, Munich, Amsterdam, and Paris need 35,000+ additional beds.",
            published_date=_days_ago(10), region=Region.EUROPE,
            topic_category=TopicCategory.EMERGING_MARKETS,
            raw_content="Full ICEF article...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Bonard",
            source_url="https://bonard.com/insights/germany-pbsa-expansion-2026",
            headline="Germany adds 8,200 PBSA beds in 2025 — record delivery",
            summary="Germany delivered a record 8,200 new PBSA beds in 2025, bringing total operational stock to 52,000 beds nationally, per Bonard. Munich (1,800 beds), Berlin (1,500), and Frankfurt (1,200) led delivery. Despite the record supply, Bonard estimates a remaining shortfall of 120,000 beds across Germany's top 20 university cities. Average rents rose 6.4% to EUR 580/month for a standard single room. Germany remains Europe's largest underserved PBSA market.",
            published_date=_days_ago(8), region=Region.EUROPE,
            topic_category=TopicCategory.SUPPLY_OUTLOOK,
            raw_content="Full Bonard report...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Study in Holland",
            source_url="https://www.studyinholland.nl/housing-crisis-update-2026",
            headline="Netherlands: 14% of international students couldn't find housing for 2025-26",
            summary="A Dutch student union survey found 14% of international students starting in the Netherlands in September 2025 could not find accommodation within the first month, up from 9% in 2024. Average waiting times for student housing in Amsterdam reached 18 months. The Dutch government's response — a proposed 30% cap on English-taught programmes — could reduce demand by 15,000 students if enacted. For operators, the housing crisis makes the Netherlands one of Europe's most attractive PBSA development markets.",
            published_date=_days_ago(6), region=Region.EUROPE,
            topic_category=TopicCategory.RENT_TRENDS,
            raw_content="Full article...", cycle_id=cycle_id,
            is_negative_news=True,
        ),
        Signal(
            signal_id="", source_name="Campus France",
            source_url="https://www.campusfrance.org/en/international-students-france-2026",
            headline="France attracts record 420,000 international students",
            summary="France hosted a record 420,000 international students in 2025-26, up 6% year-on-year, per Campus France. African students represent 46% of the total (193,000), with Morocco, Algeria, and Senegal as the top three source countries. The French government's 'Bienvenue en France' quality label programme now covers 62% of institutions. For PBSA operators, Paris (78,000 international students) and Lyon (22,000) are the primary targets, but low-cost tuition limits students' accommodation budgets.",
            published_date=_days_ago(11), region=Region.EUROPE,
            topic_category=TopicCategory.STUDENT_DEMAND,
            raw_content="Full Campus France report...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="DAAD",
            source_url="https://www.daad.de/en/study-and-research/higher-education-germany-2026",
            headline="German universities report 14% rise in non-EU applications",
            summary="Non-EU applications to German universities rose 14% for Winter Semester 2026-27, led by Indian (+28%), Turkish (+18%), and Nigerian (+22%) applicants, per DAAD data. Total international students in Germany reached 380,000, 13.5% of all enrolments. The growth is driven by Germany's tuition-free model and strong STEM reputation. PBSA operators targeting Germany should note that non-EU students are more likely to need purpose-built housing than EU students who often have wider housing networks.",
            published_date=_days_ago(7), region=Region.EUROPE,
            topic_category=TopicCategory.STUDENT_DEMAND,
            raw_content="Full DAAD report...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="The PIE News",
            source_url="https://thepienews.com/news/spain-digital-nomad-student-visa-2026",
            headline="Spain's new student visa includes accommodation requirement",
            summary="Spain's updated student visa regulations (effective March 2026) require international students to demonstrate confirmed accommodation before visa issuance — the first European country to mandate housing proof at the visa stage. An estimated 85,000 students per year will need accommodation documentation. The regulation creates a direct commercial opportunity for PBSA operators in Madrid, Barcelona, and Valencia to offer 'visa-ready' housing packages.",
            published_date=_days_ago(4), region=Region.EUROPE,
            topic_category=TopicCategory.POLICY_CHANGES,
            raw_content="Full PIE News article...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Cushman & Wakefield",
            source_url="https://www.cushmanwakefield.com/eu-pbsa-pipeline-2026",
            headline="European PBSA pipeline reaches 95,000 beds across 12 countries",
            summary="The European PBSA development pipeline totals 95,000 beds under construction or approved across 12 countries, per Cushman & Wakefield. Germany leads with 22,000 beds (23%), followed by Spain (14,000), France (12,000), and Poland (8,000). Average development yields are projected at 5.0-6.0%, above investment yields, indicating healthy development margins. Delivery is concentrated in 2027-28, which will test absorption rates in markets that have never seen institutional-scale PBSA supply.",
            published_date=_days_ago(13), region=Region.EUROPE,
            topic_category=TopicCategory.SUPPLY_OUTLOOK,
            raw_content="Full C&W report...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="University World News",
            source_url="https://www.universityworldnews.com/post/eu-erasmus-expansion-2026",
            headline="Erasmus+ programme expanded to include 8 new partner countries",
            summary="The European Commission expanded Erasmus+ programme partner status to 8 new countries including India, Brazil, and South Africa from the 2026-27 academic year, enabling funded exchange opportunities for an estimated 25,000 additional students. These exchange students typically need short-term (1-2 semester) accommodation in EU university cities. For PBSA operators, this creates a new demand segment for flexible, shorter-lease products in cities with strong Erasmus participation.",
            published_date=_days_ago(5), region=Region.EUROPE,
            topic_category=TopicCategory.POLICY_CHANGES,
            raw_content="Full UWN article...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Financial Times",
            source_url="https://www.ft.com/content/eu-student-housing-investment-2026",
            headline="Opinion: Europe's student housing is the next institutional asset class",
            summary="FT analysis argues European PBSA is following the trajectory UK student housing took 10 years ago, transitioning from fragmented private landlords to institutional-scale operations. European PBSA investment has grown from EUR 1.2bn in 2020 to EUR 4.2bn in 2025 — a 250% increase in five years. The article predicts EUR 8bn annual investment by 2030 as pension funds increase allocations. While the growth thesis is compelling, the op-ed notes planning and regulatory risks differ substantially across EU jurisdictions.",
            published_date=_days_ago(9), region=Region.EUROPE,
            topic_category=TopicCategory.SUPPLY_OUTLOOK,
            raw_content="Full FT article...", cycle_id=cycle_id,
            is_opinion=True,
        ),
    ]


def _global_signals(cycle_id: str) -> list[Signal]:
    return [
        Signal(
            signal_id="", source_name="QS",
            source_url="https://www.topuniversities.com/university-rankings/world-2026",
            headline="QS World University Rankings 2026: UK institutions gain ground",
            summary="The QS 2026 rankings show 4 UK universities moving into the top 20, with Imperial College entering the top 5 for the first time. UK institutions improved on international student ratio (+3.2 average points) and employer reputation (+2.8 points). Australian universities held steady while US institutions saw minor declines (6 of top 20 US universities dropped 1-3 places). For PBSA operators, rankings shifts correlate with application volumes 12-18 months later — cities gaining ranked universities should see demand increases.",
            published_date=_days_ago(20), region=Region.GLOBAL,
            topic_category=TopicCategory.QS_RANKINGS,
            raw_content="Full QS rankings analysis...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="Bonard",
            source_url="https://bonard.com/insights/global-pbsa-pipeline-2026",
            headline="Global PBSA pipeline reaches 450,000 beds under construction",
            summary="Bonard's global tracker counts 450,000 purpose-built student beds currently under construction worldwide as of Q1 2026. The UK accounts for 28% (126,000 beds), Australia 18% (81,000), Germany 12% (54,000), and the US 10% (45,000). Delivery is projected at 180,000 beds in 2026 and 210,000 in 2027. The pipeline represents $48 billion in development capital. For the global PBSA market, the key question is whether demand growth (currently ~5% annually) can absorb supply additions without compressing rents.",
            published_date=_days_ago(14), region=Region.GLOBAL,
            topic_category=TopicCategory.SUPPLY_OUTLOOK,
            raw_content="Full Bonard report...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="UNESCO",
            source_url="https://www.unesco.org/en/articles/global-student-mobility-2026",
            headline="Global internationally mobile students surpass 7 million",
            summary="UNESCO's latest data confirms the global internationally mobile student population exceeded 7 million in 2025, up from 6.4 million in 2023 — a 9.4% increase in two years. Intra-Asian mobility grew fastest (+15%), followed by Africa-to-Europe (+12%) and South Asia-to-Anglophone (+8%). The top 5 host countries (US, UK, Australia, Canada, Germany) collectively hold 52% market share, down from 58% in 2019 as smaller destinations gain ground. The 7M milestone reinforces the structural demand tailwind underpinning global PBSA growth.",
            published_date=_days_ago(18), region=Region.GLOBAL,
            topic_category=TopicCategory.STUDENT_DEMAND,
            raw_content="Full UNESCO report...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="ICEF Monitor",
            source_url="https://monitor.icef.com/2026/india-outbound-surge",
            headline="India's outbound student numbers hit 1.1 million — double 2019 levels",
            summary="India's total outbound student population reached 1.1 million in 2025-26, double the pre-pandemic 550,000 figure, per ICEF Monitor estimates combining MEA and host-country data. The US hosts 335,000 (30%), UK 210,000 (19%), Canada 190,000 (17%), and Australia 189,000 (17%). India has become the world's largest student-sending country, overtaking China (860,000 outbound). For PBSA operators globally, Indian student preferences (value pricing, shared accommodation, vegetarian kitchen facilities) should inform product design.",
            published_date=_days_ago(11), region=Region.GLOBAL,
            topic_category=TopicCategory.EMERGING_MARKETS,
            raw_content="Full ICEF article...", cycle_id=cycle_id,
        ),
        Signal(
            signal_id="", source_name="World Economic Forum",
            source_url="https://www.weforum.org/agenda/2026/student-housing-sustainability",
            headline="Opinion: Student housing must lead the green building transition",
            summary="A WEF agenda piece argues that student housing should be at the forefront of the global green building transition, citing evidence that Gen Z students list sustainability as a top-3 accommodation preference. The article cites data from a 12-country survey showing 68% of students would pay a 5-8% rent premium for certified green buildings. While the opinion piece advocates for mandatory sustainability ratings, the underlying demand data is relevant — operators investing in EPC upgrades and net-zero certifications can command premium rents.",
            published_date=_days_ago(16), region=Region.GLOBAL,
            topic_category=TopicCategory.SUPPLY_OUTLOOK,
            raw_content="Full WEF article...", cycle_id=cycle_id,
            is_opinion=True,
        ),
    ]


# ── Topics: 8-12 per region ───────────────────────────────────────────────

def get_sample_topics(cycle_id: str, signals: list[Signal]) -> list[Topic]:
    """Return 40 ranked sample topics (8-12 per region) derived from signals."""
    topics = []
    topics.extend(_uk_topics(cycle_id))
    topics.extend(_usa_topics(cycle_id))
    topics.extend(_au_topics(cycle_id))
    topics.extend(_eu_topics(cycle_id))
    topics.extend(_global_topics(cycle_id))
    # Sort by score descending, re-assign ranks
    topics.sort(key=lambda t: t.total_score, reverse=True)
    for i, t in enumerate(topics, 1):
        t.rank = i
        t.topic_id = f"top-{i:03d}"
    return topics


def _uk_topics(cycle_id: str) -> list[Topic]:
    return [
        Topic(cycle_id=cycle_id, title="UK Student Visa Grants Drop 12% in Q1",
              summary="Home Office data reveals 89,400 visa grants in Q1 2026 vs 101,600 in Q1 2025 — a 12% decline driven by Graduate Route reforms and higher financial requirements. Indian applicants fell 18%. This has direct occupancy implications for UK PBSA operators, especially in cities dependent on Indian and Nigerian students.",
              rank=1, urgency=UrgencyLevel.BREAKING, primary_region=Region.UK,
              secondary_regions=[Region.GLOBAL], stakeholder_tags=["Supply", "University", "HEA"],
              source_signal_ids=["sig-003", "sig-010"],
              content_guidance="Lead with 12% drop. Challenge + opportunity framing: tighter policy = premium demand.",
              urgency_score=9.0, regional_relevance_score=8.0, stakeholder_fit_score=10.0, total_score=8.95),
        Topic(cycle_id=cycle_id, title="UK PBSA Rents Surge 6.8% Year-on-Year",
              summary="Knight Frank and StuRents confirm 6.8% national rent growth with Russell Group cities at 8-9%. Supply delivery fell 15% short of targets. Northern cities outperforming London with 7-8% growth vs 0.8%.",
              rank=2, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.UK,
              stakeholder_tags=["Supply", "University"], source_signal_ids=["sig-002", "sig-008"],
              content_guidance="Lead with 6.8%. Highlight north-south divergence and supply-demand imbalance.",
              urgency_score=7.0, regional_relevance_score=8.0, stakeholder_fit_score=7.0, total_score=7.35),
        Topic(cycle_id=cycle_id, title="UCAS International Applications Up 6% to Record",
              summary="Record 145,000 international applications for Sept 2026, with Sub-Saharan Africa +23% offsetting China -5%. Nigeria +28% and Ghana +19% lead the diversification.",
              rank=3, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.UK,
              stakeholder_tags=["University", "HEA"], source_signal_ids=["sig-006"],
              content_guidance="Focus on diversification. African growth reshaping demand patterns.",
              urgency_score=6.0, regional_relevance_score=8.0, stakeholder_fit_score=7.0, total_score=6.75),
        Topic(cycle_id=cycle_id, title="HESA: International Enrolments Rise 4.2% to 758K",
              summary="UK international students rose to 758,000 with Nigerian (+31%) and Indian (+12%) growth offset by Chinese decline (-8%). Nationality mix shift changes accommodation preferences in key cities.",
              rank=4, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.UK,
              stakeholder_tags=["Supply", "University"], source_signal_ids=["sig-001"],
              content_guidance="Lead with 758K total. Angle: changing nationality mix = changing product needs.",
              urgency_score=6.0, regional_relevance_score=8.0, stakeholder_fit_score=7.0, total_score=6.75),
        Topic(cycle_id=cycle_id, title="UK PBSA Planning Approvals Fall to Five-Year Low",
              summary="Only 12,400 new PBSA beds approved in the 12 months to March 2026, down 32% from prior year. London and South East account for 48% of stalled applications. Planning bottleneck widens supply gap through 2028-29.",
              rank=5, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.UK,
              stakeholder_tags=["Supply"], source_signal_ids=["sig-007"],
              content_guidance="Supply shortage angle. Operators with approved sites hold competitive advantage.",
              urgency_score=6.0, regional_relevance_score=8.0, stakeholder_fit_score=4.0, total_score=5.90),
        Topic(cycle_id=cycle_id, title="38% of UK Students Spend 60%+ of Loan on Rent",
              summary="Unipol reports affordability crisis deepening — 38% of students spend over 60% of maintenance loan on rent, up from 31% two years ago. London ratio at 72%.",
              rank=6, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.UK,
              stakeholder_tags=["Supply", "University"], source_signal_ids=["sig-008"],
              content_guidance="Affordability angle. Regulatory and reputational risk for operators pushing rents.",
              urgency_score=5.0, regional_relevance_score=8.0, stakeholder_fit_score=7.0, total_score=6.20),
        Topic(cycle_id=cycle_id, title="MAC Recommends Maintaining Graduate Route",
              summary="MAC finds 67% of Graduate Route holders in skilled employment at 18 months — above the 60% review threshold. Reduces risk of further policy tightening near-term.",
              rank=7, urgency=UrgencyLevel.BREAKING, primary_region=Region.UK,
              stakeholder_tags=["University", "HEA"], source_signal_ids=["sig-009"],
              content_guidance="Positive recruitment signal. Use as reassurance message for 2027 intake.",
              urgency_score=9.0, regional_relevance_score=8.0, stakeholder_fit_score=7.0, total_score=8.15),
        Topic(cycle_id=cycle_id, title="UK PBSA Yields Compress to 5.0% for Prime",
              summary="Savills reports prime UK PBSA yields at 5.0%, tightest since 2019. Q1 transactions reached £1.8bn (+40% YoY) with overseas investors driving 62% of deals.",
              rank=8, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.UK,
              stakeholder_tags=["Supply"], source_signal_ids=["sig-010"],
              content_guidance="Investment angle. PBSA now firmly institutional. Overseas capital dominates.",
              urgency_score=5.0, regional_relevance_score=8.0, stakeholder_fit_score=4.0, total_score=5.55),
        Topic(cycle_id=cycle_id, title="Russell Group Grows 8% Despite Broader Visa Decline",
              summary="Russell Group captured larger share of shrinking visa pool (+8%) while non-Russell Group institutions fell 19%. Concentration trend intensifies demand in top university cities.",
              rank=9, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.UK,
              stakeholder_tags=["Supply", "University"], source_signal_ids=["sig-011"],
              content_guidance="Two-tier market emerging. Portfolio implications for operators.",
              urgency_score=6.0, regional_relevance_score=8.0, stakeholder_fit_score=7.0, total_score=6.75),
        Topic(cycle_id=cycle_id, title="Five UK Universities in Financial Distress",
              summary="OfS has five institutions under enhanced monitoring with £380m combined deficits. Three are in northern England with significant international student populations. Up to 12 could need restructuring by 2028.",
              rank=10, urgency=UrgencyLevel.BREAKING, primary_region=Region.UK,
              stakeholder_tags=["Supply", "University"], source_signal_ids=["sig-012"],
              content_guidance="Risk angle. Operators should stress-test nomination agreement exposure.",
              urgency_score=9.0, regional_relevance_score=8.0, stakeholder_fit_score=7.0, total_score=8.15,
              is_negative_news=True),
    ]


def _usa_topics(cycle_id: str) -> list[Topic]:
    return [
        Topic(cycle_id=cycle_id, title="Record US International Students Hit 1.2 Million",
              summary="IIE Open Doors data shows 1.2M international students, +7% YoY. India (335K) overtakes China (290K) as largest cohort. STEM programmes account for 56% of enrolments.",
              rank=11, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.USA,
              secondary_regions=[Region.GLOBAL], stakeholder_tags=["Supply", "HEA"],
              source_signal_ids=["sig-004"],
              content_guidance="Lead with 1.2M record. India-China shift changes demand patterns.",
              urgency_score=7.0, regional_relevance_score=6.0, stakeholder_fit_score=7.0, total_score=6.85),
        Topic(cycle_id=cycle_id, title="US Student Housing Occupancy Hits 96.2%",
              summary="NMHC reports highest US PBSA occupancy in a decade at 96.2%. Pre-leasing 8 points ahead of prior year. Sun Belt cities see 6-8% rent growth.",
              rank=12, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.USA,
              stakeholder_tags=["Supply"], source_signal_ids=["sig-013"],
              content_guidance="Demand strength angle. Sun Belt outperformance.",
              urgency_score=6.0, regional_relevance_score=6.0, stakeholder_fit_score=4.0, total_score=5.50),
        Topic(cycle_id=cycle_id, title="OPT STEM Extension Bill Could Boost US Appeal",
              summary="Bipartisan Senate bill proposes extending STEM OPT from 36 to 48 months, adding 85K student-years of residency annually. 30 universities and tech lobby support it.",
              rank=13, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.USA,
              stakeholder_tags=["University", "HEA"], source_signal_ids=["sig-015"],
              content_guidance="Forward-looking policy signal. Monitor Senate Commerce Committee progress.",
              urgency_score=6.0, regional_relevance_score=6.0, stakeholder_fit_score=7.0, total_score=6.15),
        Topic(cycle_id=cycle_id, title="US Campus Housing Shortages Hit International Students",
              summary="73% of US universities report insufficient on-campus housing for international students. 42% now partner with private PBSA operators. International students face 2.3x higher off-campus rent burdens.",
              rank=14, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.USA,
              stakeholder_tags=["Supply", "University"], source_signal_ids=["sig-016"],
              content_guidance="Partnership opportunity. Universities need PBSA operators for international student housing.",
              urgency_score=6.0, regional_relevance_score=6.0, stakeholder_fit_score=7.0, total_score=6.15),
        Topic(cycle_id=cycle_id, title="US Student Housing Investment Hits $12.8bn Record",
              summary="RealPage reports $12.8bn in US student housing transactions in 2025, surpassing 2022's $11.2bn. Core market cap rates at 4.8%. International investors comprised 28% of buyers.",
              rank=15, urgency=UrgencyLevel.EVERGREEN, primary_region=Region.USA,
              stakeholder_tags=["Supply"], source_signal_ids=["sig-014"],
              content_guidance="Investment thesis angle. Institutional capital deepening.",
              urgency_score=3.0, regional_relevance_score=6.0, stakeholder_fit_score=4.0, total_score=4.05),
        Topic(cycle_id=cycle_id, title="US Community Colleges See 22% International Surge",
              summary="International enrolments at US community colleges jumped 22%, driven by Vietnamese and Filipino students seeking affordable pathways at $9,400/year average tuition.",
              rank=16, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.USA,
              stakeholder_tags=["HEA", "Supply"], source_signal_ids=["sig-017"],
              content_guidance="Underserved niche. Affordable housing near suburban campuses.",
              urgency_score=5.0, regional_relevance_score=6.0, stakeholder_fit_score=7.0, total_score=5.70),
        Topic(cycle_id=cycle_id, title="US Student Visa Wait Times Drop to 14-Day Average",
              summary="F-1 interview wait times fell to 14 days globally from 42 days two years ago. Removes a key friction point that was redirecting students to UK and Canada.",
              rank=17, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.USA,
              stakeholder_tags=["HEA"], source_signal_ids=["sig-019"],
              content_guidance="Positive US competitive signal. Factor into agent guidance for 2027.",
              urgency_score=6.0, regional_relevance_score=6.0, stakeholder_fit_score=4.0, total_score=5.50),
        Topic(cycle_id=cycle_id, title="US PBSA Development Pipeline at Record 58,000 Beds",
              summary="JLL reports 58K new beds under construction. Texas (9.2K), Florida (7.1K), North Carolina (4.8K) lead. Development costs up 18% since 2023. Delivery concentrated 2027-28.",
              rank=18, urgency=UrgencyLevel.EVERGREEN, primary_region=Region.USA,
              stakeholder_tags=["Supply"], source_signal_ids=["sig-018"],
              content_guidance="Supply pipeline monitor. Sun Belt oversupply risk in 2027-28.",
              urgency_score=3.0, regional_relevance_score=6.0, stakeholder_fit_score=4.0, total_score=4.05),
        Topic(cycle_id=cycle_id, title="US PBSA Rent Growth Moderates to 4.2%",
              summary="CBRE reports rent growth slowing from 6.1% to 4.2% as new supply absorbs demand. Luxury tier maintains 5.5% while value tier slows to 2.8%.",
              rank=19, urgency=UrgencyLevel.EVERGREEN, primary_region=Region.USA,
              stakeholder_tags=["Supply"], source_signal_ids=["sig-020"],
              content_guidance="Market maturation angle. Focus on retention over aggressive rent increases.",
              urgency_score=3.0, regional_relevance_score=6.0, stakeholder_fit_score=4.0, total_score=4.05),
        Topic(cycle_id=cycle_id, title="SEVIS Data: Active F-1 Records Up 9%",
              summary="1.35M active F-1 records as of March 2026, +9% YoY. New initial student records +11%. CS and engineering drive 42%. North Carolina and Georgia fastest-growing states.",
              rank=20, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.USA,
              stakeholder_tags=["Supply", "HEA"], source_signal_ids=["sig-013"],
              content_guidance="Pipeline momentum. Emerging state-level growth in SE.",
              urgency_score=5.0, regional_relevance_score=6.0, stakeholder_fit_score=7.0, total_score=5.70),
    ]


def _au_topics(cycle_id: str) -> list[Topic]:
    return [
        Topic(cycle_id=cycle_id, title="Australia Sets 270K International Student Cap",
              summary="Government caps new enrolments at 270K (-8.5% from 295K). Group of Eight gets 35% quota share while private colleges face -22% cut. Creates more predictable demand for Go8-aligned operators.",
              rank=21, urgency=UrgencyLevel.BREAKING, primary_region=Region.AUSTRALIA,
              stakeholder_tags=["Supply", "University", "HEA"], source_signal_ids=["sig-023"],
              content_guidance="Major policy shift. Go8 partnership operators least affected.",
              urgency_score=9.0, regional_relevance_score=6.0, stakeholder_fit_score=10.0, total_score=8.00),
        Topic(cycle_id=cycle_id, title="Australian PBSA Rents Jump 9.3% — Fastest Globally",
              summary="Knight Frank reports 9.3% YoY rent growth with vacancy at record low: 0.8% Melbourne, 1.1% Sydney. AUD 485/week average for studios. Pipeline covers only 30% of shortage.",
              rank=22, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.AUSTRALIA,
              stakeholder_tags=["Supply"], source_signal_ids=["sig-022"],
              content_guidance="Lead with 9.3% — fastest growth globally. Supply shortage acute.",
              urgency_score=7.0, regional_relevance_score=6.0, stakeholder_fit_score=4.0, total_score=5.95),
        Topic(cycle_id=cycle_id, title="Australia Visa Processing Extended to 8-12 Weeks",
              summary="DHA extends processing from 4-6 to 8-12 weeks citing housing constraints. Grant rates fell 6pp to 82%. Housing availability now directly linked to visa processing.",
              rank=23, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.AUSTRALIA,
              stakeholder_tags=["Supply", "University", "HEA"], source_signal_ids=["sig-021"],
              content_guidance="Housing-visa linkage. Operators can offer accommodation guarantees.",
              urgency_score=7.0, regional_relevance_score=6.0, stakeholder_fit_score=10.0, total_score=7.30),
        Topic(cycle_id=cycle_id, title="Indian Students Overtake Chinese in Australia",
              summary="Indian students now 27% of Australian international enrolments (189K) vs Chinese 24% (168K). Indian numbers +14%, Chinese -6%. Shift changes accommodation preferences toward value-tier shared product.",
              rank=24, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.AUSTRALIA,
              stakeholder_tags=["Supply", "HEA"], source_signal_ids=["sig-025"],
              content_guidance="Nationality shift angle. Product design implications.",
              urgency_score=6.0, regional_relevance_score=6.0, stakeholder_fit_score=7.0, total_score=6.15),
        Topic(cycle_id=cycle_id, title="42,000-Bed Shortfall Projected in Australia by 2028",
              summary="Deloitte projects AUD 8.4bn investment needed. Melbourne (-15K beds), Sydney (-12K), Brisbane (-8K) face largest gaps. Market could double in 5 years.",
              rank=25, urgency=UrgencyLevel.EVERGREEN, primary_region=Region.AUSTRALIA,
              stakeholder_tags=["Supply"], source_signal_ids=["sig-024"],
              content_guidance="Opportunity quantification. Scale of investment needed.",
              urgency_score=3.0, regional_relevance_score=6.0, stakeholder_fit_score=4.0, total_score=4.05),
        Topic(cycle_id=cycle_id, title="Australian PBSA Investment Hits AUD 3.1bn Record",
              summary="Savills reports 35% YoY growth to AUD 3.1bn. Singaporean and Canadian pension funds lead at 58% of transactions. Melbourne 42%, Sydney 31%, Brisbane 18%.",
              rank=26, urgency=UrgencyLevel.EVERGREEN, primary_region=Region.AUSTRALIA,
              stakeholder_tags=["Supply"], source_signal_ids=["sig-026"],
              content_guidance="Investment thesis. Australia fastest-growing institutional PBSA market.",
              urgency_score=3.0, regional_relevance_score=6.0, stakeholder_fit_score=4.0, total_score=4.05),
        Topic(cycle_id=cycle_id, title="Australia VET International Enrolments Surge 18%",
              summary="VET sector outpacing university growth with 210K international students. Cookery, aged care, IT courses drive demand from South and SE Asian students.",
              rank=27, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.AUSTRALIA,
              stakeholder_tags=["HEA", "Supply"], source_signal_ids=["sig-027"],
              content_guidance="Underserved segment. Affordable suburban PBSA opportunity.",
              urgency_score=5.0, regional_relevance_score=6.0, stakeholder_fit_score=7.0, total_score=5.70),
        Topic(cycle_id=cycle_id, title="Regional Aus Universities Offer Free Accommodation",
              summary="Six regional universities offering free/subsidised accommodation for first semester, covering 2,400 beds. 78% take-up rate. Could redistribute demand from capital cities.",
              rank=28, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.AUSTRALIA,
              stakeholder_tags=["University", "Supply"], source_signal_ids=["sig-028"],
              content_guidance="Demand redistribution signal. Monitor impact on capital city occupancy.",
              urgency_score=5.0, regional_relevance_score=6.0, stakeholder_fit_score=7.0, total_score=5.70),
        Topic(cycle_id=cycle_id, title="Australia Mandates Agent Registration from July",
              summary="All education agents must register with national body. 4,500 agents globally affected. Non-compliance blocks visa processing. Professionalises sector.",
              rank=29, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.AUSTRALIA,
              stakeholder_tags=["HEA"], source_signal_ids=["sig-029"],
              content_guidance="Compliance angle for agents. Early registration = competitive advantage.",
              urgency_score=6.0, regional_relevance_score=6.0, stakeholder_fit_score=4.0, total_score=5.50),
        Topic(cycle_id=cycle_id, title="BTR Developers Pivot to PBSA in Australia",
              summary="Mirvac, Lendlease, Grocon commit 8,500 beds for 2028-29. PBSA yields (5.2%) beat BTR (4.4%). Total pipeline now 26,000+ beds. Competition intensifying near Go8 campuses.",
              rank=30, urgency=UrgencyLevel.EVERGREEN, primary_region=Region.AUSTRALIA,
              stakeholder_tags=["Supply"], source_signal_ids=["sig-030"],
              content_guidance="New competition angle. Major BTR players entering PBSA.",
              urgency_score=3.0, regional_relevance_score=6.0, stakeholder_fit_score=4.0, total_score=4.05),
    ]


def _eu_topics(cycle_id: str) -> list[Topic]:
    return [
        Topic(cycle_id=cycle_id, title="African Student Mobility to Europe Surges 18%",
              summary="ICEF reports 18% growth in African students choosing Europe. France (42K, +14%), Germany (28K, +22%), Netherlands (15K, +19%). Tuition-free programmes are primary draw. Berlin, Munich, Amsterdam need 35K+ more beds.",
              rank=31, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.EUROPE,
              secondary_regions=[Region.GLOBAL], stakeholder_tags=["Supply", "HEA"],
              source_signal_ids=["sig-032"],
              content_guidance="Emerging corridor opportunity. PBSA demand in cities with limited stock.",
              urgency_score=5.0, regional_relevance_score=7.0, stakeholder_fit_score=7.0, total_score=6.10),
        Topic(cycle_id=cycle_id, title="European PBSA Investment Hits EUR 4.2 Billion",
              summary="JLL reports 22% YoY growth. Germany EUR 1.4bn, Netherlands EUR 850m. Poland (EUR 280m) and Portugal (EUR 190m) hit record volumes. 15-country institutional base now.",
              rank=32, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.EUROPE,
              stakeholder_tags=["Supply"], source_signal_ids=["sig-031"],
              content_guidance="Market maturation angle. Investment following demand into new markets.",
              urgency_score=5.0, regional_relevance_score=7.0, stakeholder_fit_score=4.0, total_score=5.20),
        Topic(cycle_id=cycle_id, title="Germany Adds Record 8,200 PBSA Beds in 2025",
              summary="Bonard reports record delivery but 120K-bed shortfall remains across top 20 cities. Munich, Berlin, Frankfurt lead. Rents +6.4% to EUR 580/month. Europe's largest underserved market.",
              rank=33, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.EUROPE,
              stakeholder_tags=["Supply"], source_signal_ids=["sig-033"],
              content_guidance="Scale of German opportunity. 120K shortfall despite record delivery.",
              urgency_score=5.0, regional_relevance_score=7.0, stakeholder_fit_score=4.0, total_score=5.20),
        Topic(cycle_id=cycle_id, title="Netherlands: 14% of International Students Couldn't Find Housing",
              summary="Dutch student union survey: 14% of new international students homeless first month, up from 9%. Amsterdam wait times at 18 months. Government may cap English-taught programmes.",
              rank=34, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.EUROPE,
              stakeholder_tags=["Supply", "University"], source_signal_ids=["sig-034"],
              content_guidance="Crisis = opportunity. Netherlands among Europe's most attractive PBSA markets.",
              urgency_score=6.0, regional_relevance_score=7.0, stakeholder_fit_score=7.0, total_score=6.40),
        Topic(cycle_id=cycle_id, title="France Attracts Record 420K International Students",
              summary="Campus France reports 6% growth to 420K. African students 46% of total (193K). Paris (78K) and Lyon (22K) primary targets but low tuition limits accommodation budgets.",
              rank=35, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.EUROPE,
              stakeholder_tags=["Supply", "HEA"], source_signal_ids=["sig-035"],
              content_guidance="Scale of French market. Budget-constrained demand segment.",
              urgency_score=5.0, regional_relevance_score=7.0, stakeholder_fit_score=7.0, total_score=6.10),
        Topic(cycle_id=cycle_id, title="German Universities See 14% Rise in Non-EU Applications",
              summary="DAAD reports Indian (+28%), Turkish (+18%), Nigerian (+22%) applications leading growth. 380K international students total, 13.5% of enrolments. Non-EU students more likely to need PBSA.",
              rank=36, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.EUROPE,
              stakeholder_tags=["University", "HEA"], source_signal_ids=["sig-036"],
              content_guidance="Demand growth in Germany. Non-EU applicants = PBSA target segment.",
              urgency_score=5.0, regional_relevance_score=7.0, stakeholder_fit_score=7.0, total_score=6.10),
        Topic(cycle_id=cycle_id, title="Spain Mandates Accommodation Proof for Student Visa",
              summary="Spain requires confirmed accommodation before visa issuance from March 2026 — first in Europe. 85K students/year affected. Direct commercial opportunity for 'visa-ready' PBSA packages.",
              rank=37, urgency=UrgencyLevel.BREAKING, primary_region=Region.EUROPE,
              stakeholder_tags=["Supply", "HEA"], source_signal_ids=["sig-037"],
              content_guidance="New regulatory opportunity. Housing-visa linkage in Spain.",
              urgency_score=8.0, regional_relevance_score=7.0, stakeholder_fit_score=7.0, total_score=7.30),
        Topic(cycle_id=cycle_id, title="European PBSA Pipeline Reaches 95,000 Beds",
              summary="Cushman & Wakefield: 95K beds across 12 countries. Germany 22K (23%), Spain 14K, France 12K, Poland 8K. Development yields 5.0-6.0%. Delivery concentrated 2027-28.",
              rank=38, urgency=UrgencyLevel.EVERGREEN, primary_region=Region.EUROPE,
              stakeholder_tags=["Supply"], source_signal_ids=["sig-038"],
              content_guidance="Pipeline monitor. Absorption rate test in markets new to institutional PBSA.",
              urgency_score=3.0, regional_relevance_score=7.0, stakeholder_fit_score=4.0, total_score=4.40),
        Topic(cycle_id=cycle_id, title="Erasmus+ Expands to India, Brazil, South Africa",
              summary="EU Commission adds 8 partner countries to Erasmus+ from 2026-27. 25K additional exchange students need short-term accommodation. Flexible lease demand in EU university cities.",
              rank=39, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.EUROPE,
              stakeholder_tags=["University", "Supply"], source_signal_ids=["sig-039"],
              content_guidance="New demand segment. Flexible short-lease PBSA products.",
              urgency_score=5.0, regional_relevance_score=7.0, stakeholder_fit_score=7.0, total_score=6.10),
    ]


def _global_topics(cycle_id: str) -> list[Topic]:
    return [
        Topic(cycle_id=cycle_id, title="Global Student Mobility Surpasses 7 Million",
              summary="UNESCO confirms 7M+ internationally mobile students, +9.4% in two years. Top 5 hosts hold 52% share (down from 58% in 2019). Structural demand tailwind for PBSA.",
              rank=40, urgency=UrgencyLevel.EVERGREEN, primary_region=Region.GLOBAL,
              stakeholder_tags=["Supply", "HEA"], source_signal_ids=["sig-043"],
              content_guidance="Macro trend. Structural growth underpins PBSA sector.",
              urgency_score=3.0, regional_relevance_score=10.0, stakeholder_fit_score=7.0, total_score=5.80),
        Topic(cycle_id=cycle_id, title="Global PBSA Pipeline Reaches 450,000 Beds",
              summary="Bonard: 450K beds under construction. UK 28%, Australia 18%, Germany 12%, US 10%. $48bn in development capital. Key question: can 5% annual demand growth absorb supply?",
              rank=41, urgency=UrgencyLevel.EVERGREEN, primary_region=Region.GLOBAL,
              stakeholder_tags=["Supply"], source_signal_ids=["sig-042"],
              content_guidance="Supply-demand balance. Monitor absorption rates.",
              urgency_score=3.0, regional_relevance_score=10.0, stakeholder_fit_score=4.0, total_score=4.75),
        Topic(cycle_id=cycle_id, title="India Sends 1.1M Students Abroad — Double 2019",
              summary="ICEF: India now world's largest student sender at 1.1M, overtaking China (860K). US 30%, UK 19%, Canada 17%, Australia 17%. Product design should reflect Indian preferences.",
              rank=42, urgency=UrgencyLevel.TIME_SENSITIVE, primary_region=Region.GLOBAL,
              stakeholder_tags=["Supply", "HEA"], source_signal_ids=["sig-044"],
              content_guidance="India as dominant demand driver. Product and pricing implications.",
              urgency_score=5.0, regional_relevance_score=10.0, stakeholder_fit_score=7.0, total_score=6.60),
        Topic(cycle_id=cycle_id, title="QS Rankings 2026: UK Gains, US Slips",
              summary="4 UK universities enter QS top 20. Imperial reaches top 5. Australian institutions steady. US sees minor declines. Rankings correlate with applications 12-18 months out.",
              rank=43, urgency=UrgencyLevel.EVERGREEN, primary_region=Region.GLOBAL,
              stakeholder_tags=["University", "HEA"], source_signal_ids=["sig-041"],
              content_guidance="Rankings as demand predictor. UK cities gaining ranked unis = rising demand.",
              urgency_score=3.0, regional_relevance_score=5.0, stakeholder_fit_score=7.0, total_score=4.60),
    ]


def get_sample_shortlisted_topics(cycle_id: str, signals: list[Signal]) -> list[Topic]:
    """Return top 5 per region shortlisted topics for LinkedIn/Blog/Newsletter."""
    all_topics = get_sample_topics(cycle_id, signals)
    # Pick top 5 per region by rank
    region_order = ["UK", "USA", "Australia", "Europe", "Global"]
    shortlisted = []
    for region in region_order:
        region_topics = [t for t in all_topics if t.primary_region.value == region]
        region_topics.sort(key=lambda t: t.rank)
        limit = 3 if region == "Global" else 5
        shortlisted.extend(region_topics[:limit])
    return shortlisted


# ── Newsroom Blog Items: 7-12 per region, 21-25 words each ────────────

def get_sample_newsroom_items(cycle_id: str, topics: list[Topic]) -> dict[str, list[dict]]:
    """Return sample Amber Beat newsroom blog items grouped by region."""
    return {
        "UK": [
            {"item_text": "UK student visa grants fell 12% in Q1 2026 to 89,400, driven by stricter Graduate Route eligibility and higher financial requirements. (Home Office)", "topic_id": "top-001", "source_url": "https://www.gov.uk/government/statistics/immigration-q1-2026", "word_count": 24, "valid": True},
            {"item_text": "MAC recommends maintaining the Graduate Route after finding 67% of holders in skilled employment at 18 months, above the 60% review threshold. (GOV.UK)", "topic_id": "top-007", "source_url": "https://www.gov.uk/government/publications/mac-annual-report-2026", "word_count": 24, "valid": True},
            {"item_text": "UK PBSA rents rose 6.8% nationally in 2025-26 with Russell Group cities at 8-9%, while new supply delivery fell 15% short of targets. (Knight Frank)", "topic_id": "top-002", "source_url": "https://www.knightfrank.co.uk/research/uk-pbsa-2026", "word_count": 25, "valid": True},
            {"item_text": "International applications for September 2026 UK entry rose 6% to a record 145,000, with Sub-Saharan Africa up 23%. (UCAS)", "topic_id": "top-003", "source_url": "https://www.ucas.com/data-and-analysis/applicant-data-2026", "word_count": 21, "valid": True},
            {"item_text": "HESA data shows UK international student numbers rose 4.2% to 758,000, led by Nigerian enrolments surging 31% year-on-year. (HESA)", "topic_id": "top-004", "source_url": "https://www.hesa.ac.uk/news/2026/student-numbers", "word_count": 21, "valid": True},
            {"item_text": "Only 12,400 new PBSA beds received planning approval in 12 months to March 2026, a 32% drop and five-year low. (Property Week)", "topic_id": "top-005", "source_url": "https://www.propertyweek.com/news/pbsa-planning-approvals-2026", "word_count": 22, "valid": True},
            {"item_text": "Unipol reports 38% of UK students now spend over 60% of their maintenance loan on rent, up from 31% two years ago. (Unipol)", "topic_id": "top-006", "source_url": "https://www.unipol.org.uk/research/affordability-report-2026", "word_count": 23, "valid": True},
            {"item_text": "Prime UK PBSA yields compressed 25 basis points to 5.0% in Q1 2026, with overseas investors driving 62% of transactions. (Savills)", "topic_id": "top-008", "source_url": "https://www.savills.co.uk/research/student-accommodation-2026", "word_count": 22, "valid": True},
            {"item_text": "Russell Group universities grew international intake 8% despite the broader 12% visa decline, while non-Russell Group fell 19%. (ICEF Monitor)", "topic_id": "top-009", "source_url": "https://monitor.icef.com/2026/uk-russell-group-intl-growth", "word_count": 22, "valid": True},
            {"item_text": "The Office for Students has five UK universities under enhanced financial monitoring with combined deficits totalling £380 million. (The Guardian)", "topic_id": "top-010", "source_url": "https://www.theguardian.com/education/2026/uk-university-finances", "word_count": 21, "valid": True},
        ],
        "USA": [
            {"item_text": "US international student numbers reached a record 1.2 million in 2025-26, with Indian students overtaking Chinese as the largest cohort. (IIE)", "topic_id": "top-011", "source_url": "https://www.iie.org/research/open-doors-2026", "word_count": 22, "valid": True},
            {"item_text": "A bipartisan Senate bill proposes extending STEM OPT from 36 to 48 months, adding an estimated 85,000 student-years of US residency. (Inside Higher Ed)", "topic_id": "top-013", "source_url": "https://www.insidehighered.com/news/2026/opt-stem-extensions", "word_count": 23, "valid": True},
            {"item_text": "US purpose-built student housing occupancy reached 96.2% for Fall 2025, the highest in a decade, with Sun Belt cities at 6-8% rent growth. (NMHC)", "topic_id": "top-012", "source_url": "https://www.nmhc.org/research/student-housing-outlook-2026", "word_count": 24, "valid": True},
            {"item_text": "73% of US universities report insufficient on-campus housing for international students, with 42% now partnering with private PBSA operators. (Chronicle)", "topic_id": "top-014", "source_url": "https://www.chronicle.com/article/us-housing-crisis-international-2026", "word_count": 22, "valid": True},
            {"item_text": "SEVIS data shows 1.35 million active F-1 student records as of March 2026, up 9% year-on-year with new enrolments rising 11%. (SEVP)", "topic_id": "top-020", "source_url": "https://studyinthestates.dhs.gov/sevis-data-2026", "word_count": 23, "valid": True},
            {"item_text": "International enrolments at US community colleges jumped 22% in Fall 2025, driven by Vietnamese and Filipino students seeking affordable pathways. (ICEF Monitor)", "topic_id": "top-016", "source_url": "https://monitor.icef.com/2026/us-community-college-international", "word_count": 22, "valid": True},
            {"item_text": "US student visa interview wait times dropped to a 14-day global average in Q1 2026, down from 42 days in Q1 2024. (Forbes)", "topic_id": "top-017", "source_url": "https://www.forbes.com/advisor/education/us-visa-processing-delays-2026", "word_count": 22, "valid": True},
            {"item_text": "JLL reports 58,000 new student housing beds under construction across the US, a 15% increase year-on-year led by Texas and Florida. (JLL)", "topic_id": "top-018", "source_url": "https://www.jll.com/en/research/us-student-housing-q1-2026", "word_count": 22, "valid": True},
        ],
        "Australia": [
            {"item_text": "Australian Government confirmed a cap of 270,000 new international student enrolments for 2026, an 8.5% reduction from 295,000 in 2025. (Australian Government)", "topic_id": "top-021", "source_url": "https://www.education.gov.au/international-education-data-2026", "word_count": 23, "valid": True},
            {"item_text": "DHA extended student visa processing from 4-6 weeks to 8-12 weeks, citing accommodation capacity constraints in Sydney, Melbourne and Brisbane. (DHA)", "topic_id": "top-023", "source_url": "https://www.homeaffairs.gov.au/research/student-visa-statistics", "word_count": 22, "valid": True},
            {"item_text": "Australian PBSA rents rose 9.3% year-on-year in Q1 2026, the fastest growth globally, with vacancy rates at a record 0.8% in Melbourne. (Knight Frank)", "topic_id": "top-022", "source_url": "https://www.knightfrank.com.au/research/au-pbsa-market-2026", "word_count": 24, "valid": True},
            {"item_text": "Indian students now represent 27% of all international enrolments in Australia at 189,000, overtaking Chinese students at 24% for the first time. (SBS News)", "topic_id": "top-024", "source_url": "https://www.sbs.com.au/news/indian-students-australia-2026", "word_count": 23, "valid": True},
            {"item_text": "Deloitte projects a 42,000-bed shortfall in Australian purpose-built student accommodation by 2028, requiring AUD 8.4 billion in investment. (The Australian)", "topic_id": "top-025", "source_url": "https://www.theaustralian.com.au/higher-ed/student-housing-crisis-2026", "word_count": 22, "valid": True},
            {"item_text": "Australian PBSA investment hit a record AUD 3.1 billion in 2025, up 35% year-on-year, with Singaporean and Canadian pension funds leading. (Savills)", "topic_id": "top-026", "source_url": "https://www.savills.com.au/research/pbsa-investment-au-2026", "word_count": 23, "valid": True},
            {"item_text": "Australia's VET sector international enrolments grew 18% to 210,000 students, outpacing the university sector's 4% growth rate. (ICEF Monitor)", "topic_id": "top-027", "source_url": "https://monitor.icef.com/2026/australia-vet-sector-international", "word_count": 21, "valid": True},
            {"item_text": "Six regional Australian universities now offer free first-semester accommodation to attract international students from overcrowded capital cities. (ABC News)", "topic_id": "top-028", "source_url": "https://www.abc.net.au/news/2026/regional-australia-student-housing", "word_count": 21, "valid": True},
            {"item_text": "Australia will require all education agents to register with a national body from July 2026, affecting an estimated 4,500 agents globally. (The PIE News)", "topic_id": "top-029", "source_url": "https://thepienews.com/news/australia-agent-regulation-2026", "word_count": 22, "valid": True},
        ],
        "Europe": [
            {"item_text": "Spain now requires international students to demonstrate confirmed accommodation before visa issuance — the first European country to mandate housing proof. (The PIE News)", "topic_id": "top-037", "source_url": "https://thepienews.com/news/spain-digital-nomad-student-visa-2026", "word_count": 23, "valid": True},
            {"item_text": "African students choosing European destinations grew 18%, with France receiving 42,000 new students, Germany 28,000 and the Netherlands 15,000. (ICEF Monitor)", "topic_id": "top-031", "source_url": "https://monitor.icef.com/2026/emerging-corridors-africa", "word_count": 22, "valid": True},
            {"item_text": "Non-EU applications to German universities rose 14% for Winter 2026-27, led by Indian applicants up 28% and Nigerian applicants up 22%. (DAAD)", "topic_id": "top-036", "source_url": "https://www.daad.de/en/study-and-research/higher-education-germany-2026", "word_count": 22, "valid": True},
            {"item_text": "14% of international students starting in the Netherlands in September 2025 could not find accommodation within the first month, up from 9%. (Study in Holland)", "topic_id": "top-034", "source_url": "https://www.studyinholland.nl/housing-crisis-update-2026", "word_count": 24, "valid": True},
            {"item_text": "European PBSA investment volumes hit EUR 4.2 billion in 2025, a 22% increase, with Germany and the Netherlands leading activity. (JLL)", "topic_id": "top-032", "source_url": "https://www.jll.co.uk/en/research/european-pbsa-outlook", "word_count": 21, "valid": True},
            {"item_text": "Germany delivered a record 8,200 new PBSA beds in 2025 but Bonard estimates a remaining shortfall of 120,000 beds across the top 20 cities. (Bonard)", "topic_id": "top-033", "source_url": "https://bonard.com/insights/germany-pbsa-expansion-2026", "word_count": 24, "valid": True},
            {"item_text": "France attracted a record 420,000 international students in 2025-26, up 6% year-on-year, with African students representing 46% of the total. (Campus France)", "topic_id": "top-035", "source_url": "https://www.campusfrance.org/en/international-students-france-2026", "word_count": 23, "valid": True},
            {"item_text": "Erasmus+ programme expanded to include India, Brazil and South Africa from 2026-27, enabling funded exchanges for 25,000 additional students. (EU Commission)", "topic_id": "top-039", "source_url": "https://www.universityworldnews.com/post/eu-erasmus-expansion-2026", "word_count": 22, "valid": True},
            {"item_text": "The European PBSA development pipeline totals 95,000 beds under construction across 12 countries, with Germany leading at 22,000 beds. (Cushman & Wakefield)", "topic_id": "top-038", "source_url": "https://www.cushmanwakefield.com/eu-pbsa-pipeline-2026", "word_count": 22, "valid": True},
        ],
        "Global": [
            {"item_text": "India's total outbound student population reached 1.1 million in 2025-26, double the pre-pandemic figure, making it the world's largest student sender. (ICEF Monitor)", "topic_id": "top-042", "source_url": "https://monitor.icef.com/2026/india-outbound-surge", "word_count": 24, "valid": True},
            {"item_text": "Global internationally mobile students exceeded 7 million in 2025, up 9.4% in two years, with the top 5 hosts holding 52% market share. (UNESCO)", "topic_id": "top-040", "source_url": "https://www.unesco.org/en/articles/global-student-mobility-2026", "word_count": 23, "valid": True},
            {"item_text": "Bonard counts 450,000 purpose-built student beds under construction worldwide, representing $48 billion in development capital across 25 countries. (Bonard)", "topic_id": "top-041", "source_url": "https://bonard.com/insights/global-pbsa-pipeline-2026", "word_count": 21, "valid": True},
            {"item_text": "QS 2026 rankings show four UK universities entering the top 20, with Imperial College reaching the top 5 for the first time. (QS)", "topic_id": "top-043", "source_url": "https://www.topuniversities.com/university-rankings/world-2026", "word_count": 22, "valid": True},
        ],
    }


# ── LinkedIn / Blog / Newsletter sample drafts (unchanged in structure) ───

def get_sample_linkedin_draft(topic: Topic, voice: DraftVoice, cycle_id: str) -> ContentDraft:
    """Generate a realistic sample LinkedIn post for a given topic and voice."""
    voice_content = {
        DraftVoice.AMBER_BRAND: _amber_brand_post,
        DraftVoice.MADHUR: _madhur_post,
        DraftVoice.JOOLS: _jools_post,
    }
    generator = voice_content.get(voice, _amber_brand_post)
    body = generator(topic)
    return ContentDraft(
        draft_id=f"li-{topic.topic_id}-{voice.value[:3].lower()}",
        cycle_id=cycle_id,
        topic_id=topic.topic_id,
        channel=DraftChannel.LINKEDIN,
        audience=StakeholderAudience.SUPPLY if "Supply" in topic.stakeholder_tags else StakeholderAudience.UNIVERSITY,
        voice=voice,
        content_body=body,
        word_count=len(body.split()),
        generation_prompt="[dev mode — sample data]",
        generation_model="sample-data",
        status=DraftStatus.DRAFT,
    )


def get_sample_blog_draft(topic: Topic, audience: StakeholderAudience, voice: DraftVoice, cycle_id: str) -> ContentDraft:
    """Generate a realistic sample blog post."""
    body = f"""# {topic.edited_title or topic.title}: What It Means for {audience.value} Partners

The latest data confirms what many in the sector have been anticipating. {topic.summary}

## What the Data Shows

[STAT] {topic.edited_title or topic.title} — the numbers speak clearly.

The trend is unmistakable. Across our key markets, we're seeing a fundamental shift in how the international student accommodation landscape is evolving. This isn't a blip — it's a structural change that demands attention from every stakeholder in the sector.

The data from multiple sources corroborates this picture. Whether you look at official government statistics or independent market research, the direction is consistent.

## What This Means for {audience.value} Partners

For {audience.value.lower()} partners specifically, this development creates both challenges and opportunities. The challenge is clear: the operating environment is becoming more complex. But complexity creates opportunity for those who are prepared.

Organisations that have invested in data-driven decision-making and strategic partnerships will be best positioned to navigate this shift. The key is to act now rather than wait for the trend to fully materialise.

## What to Watch Next

The next 6-12 months will be critical. We expect further policy developments that will shape the landscape for years to come. Stay close to the data, and stay close to partners who can help you interpret it.

[STAT] Key figure: {topic.edited_title or topic.title}

**Ready to discuss how this affects your portfolio? [Contact our team](https://amber.com/contact)**"""

    return ContentDraft(
        draft_id=f"blog-{topic.topic_id}-{audience.value[:3].lower()}",
        cycle_id=cycle_id,
        topic_id=topic.topic_id,
        channel=DraftChannel.BLOG,
        audience=audience,
        voice=voice,
        content_body=body,
        word_count=len(body.split()),
        generation_prompt="[dev mode — sample data]",
        generation_model="sample-data",
        status=DraftStatus.DRAFT,
    )


def get_sample_newsletter(cycle_id: str, signals: list[Signal]) -> ContentDraft:
    """Generate a realistic sample bimonthly newsletter."""
    # Pick best signal per region
    uk_sig = next((s for s in signals if s.region == Region.UK), signals[0])
    us_sig = next((s for s in signals if s.region == Region.USA), signals[0])
    au_sig = next((s for s in signals if s.region == Region.AUSTRALIA), signals[0])
    eu_sig = next((s for s in signals if s.region == Region.EUROPE), signals[0])

    body = f"""# amber beat | April 2026

**This month: visa pressure, rent growth, and emerging corridors reshaping the global student housing landscape.**

*Bimonthly newsletter — curated from the Amber Beat newsroom blog*

---

## UK

{uk_sig.headline}. {uk_sig.summary.split('.')[0]}. For UK PBSA operators, this data point reinforces the importance of quality accommodation in a tightening market — those with strong university partnerships and premium stock will continue to outperform.

## USA

{us_sig.headline}. {us_sig.summary.split('.')[0]}. With Indian students now the largest cohort, operators and agents should be rethinking their outreach strategies and accommodation preferences for this demographic.

## Australia

{au_sig.headline}. {au_sig.summary.split('.')[0]}. While processing delays create short-term uncertainty, the underlying demand fundamentals remain strong — students want to study in Australia, and quality housing will be a key differentiator.

## Europe

{eu_sig.headline}. {eu_sig.summary.split('.')[0]}. This represents a significant emerging corridor that forward-thinking PBSA investors and education agents should be monitoring closely.

---

**Quick Stats:** UK rents +6.8% | US students 1.2M record | AU visa times 8-12 weeks | EU PBSA investment EUR 4.2bn

---

*amber — where students live, learn, and thrive.*
*[Unsubscribe](https://amber.com/unsubscribe) | [Preferences](https://amber.com/preferences)*"""

    return ContentDraft(
        draft_id=f"nl-{cycle_id}",
        cycle_id=cycle_id,
        topic_id="newsletter",
        channel=DraftChannel.NEWSLETTER,
        audience=None,
        voice=DraftVoice.NEWSLETTER_GLOBAL,
        content_body=body,
        word_count=len(body.split()),
        generation_prompt="[dev mode — sample data]",
        generation_model="sample-data",
        status=DraftStatus.DRAFT,
    )


# -- LinkedIn post generators per voice --

def _amber_brand_post(topic: Topic) -> str:
    return f"""The data is in — and it demands attention.

{topic.summary}

At amber, we see this as a pivotal moment for the student accommodation sector. Our data across {topic.primary_region} and beyond confirms what the headline numbers suggest: the market is shifting, and operators who rely on outdated assumptions will be caught off guard.

What does this mean in practice?

For our supply partners: the yield opportunity is real, but it requires strategic positioning. We're seeing the strongest returns in markets where supply quality meets genuine student demand.

For our university partners: student housing is no longer a back-office concern — it's a recruitment differentiator.

We're publishing our full analysis on the amber blog this week. In the meantime, we'd love to hear your take.

What are you seeing on the ground?

#StudentHousing #PBSA #InternationalStudents #HigherEducation"""


def _madhur_post(topic: Topic) -> str:
    return f"""Here's what nobody's saying about {topic.edited_title or topic.title}:

{topic.summary}

I've been watching this trend for months, and I think the market is underreacting. Everyone's focused on the headline number, but the real story is in the second-order effects.

When you see a shift like this, the question isn't "is this good or bad?" — it's "who's positioned to benefit, and who isn't?"

At amber, we've been building our strategy around exactly this scenario. Not because we predicted the specific numbers, but because we built a platform that thrives on market complexity.

The operators who will win in the next 24 months aren't the ones with the most beds. They're the ones with the best data, the strongest partnerships, and the willingness to move fast.

I'll be sharing more detailed analysis at our next investor briefing. DM me if you'd like an invite."""


def _jools_post(topic: Topic) -> str:
    return f"""I had three conversations with university housing directors this week. Every single one mentioned {topic.edited_title or topic.title.lower()}.

{topic.summary}

Here's what strikes me: universities are increasingly recognising that accommodation isn't just about beds — it's about the complete student experience, and it's becoming a genuine factor in international recruitment.

The institutions getting this right are the ones treating their housing partnerships as strategic, not transactional. They're asking the right questions: how does our accommodation offer compare to our competitors? Are we losing students at the accommodation stage?

I see this as an enormous opportunity for universities and quality PBSA operators to work more closely together. The data supports deeper collaboration, and the students benefit when it happens.

If you're in a university accommodation or partnerships role and want to discuss what we're seeing across the sector, I'm always happy to chat."""
