import streamlit as st
import os
import json
import time
from typing import List, Optional
from pydantic import BaseModel, Field
from firecrawl import Firecrawl
from agno.agent import Agent
from agno.models.groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Load from Streamlit Secrets if running on cloud
try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
    if "FIRECRAWL_API_KEY" in st.secrets:
        os.environ["FIRECRAWL_API_KEY"] = st.secrets["FIRECRAWL_API_KEY"]
except Exception:
    pass  # Running locally — keys loaded from .env

groq_key = os.getenv("GROQ_API_KEY", "")
firecrawl_key = os.getenv("FIRECRAWL_API_KEY", "")

# --- Page Config ---
st.set_page_config(
    page_title="Hindustan Realty AI",
    page_icon="🏠",
    layout="wide",
)

st.markdown("""
<style>
    .price-tag { color: #FF4B4B; font-size: 1.2rem; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- Pydantic Schema ---
class PropertyListing(BaseModel):
    address: str = Field(..., description="Full address or location of the property")
    price_inr: str = Field(..., description="Price in INR e.g. 85 Lakhs, 1.2 Cr")
    bhk: str = Field(..., description="BHK config e.g. 2 BHK, 3 BHK")
    area_sqft: str = Field(..., description="Area in sqft or sq yards")
    listing_url: str = Field(..., description="Direct URL to the property listing")
    builder_name: Optional[str] = Field(None, description="Builder or project name")
    amenities: List[str] = Field(default_factory=list, description="Key amenities")

# --- Retry Helper ---
def call_agent_with_retry(agent, prompt, retries=3):
    for attempt in range(retries):
        try:
            return agent.run(prompt)
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait = 30 * (attempt + 1)
                st.toast(f"⏳ Rate limit — retrying in {wait}s (attempt {attempt+2}/{retries})...")
                time.sleep(wait)
            else:
                raise e

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Settings & Filters")

    st.subheader("🏘 Property Filters")
    city = st.text_input("City", value="Gurgaon")
    locality = st.text_input("Locality", value="Sector 57")

    col1, col2 = st.columns(2)
    with col1:
        min_budget = st.number_input("Min (₹L)", value=50, min_value=5, max_value=10000)
    with col2:
        max_budget = st.number_input("Max (₹L)", value=250, min_value=5, max_value=10000)

    bhk_config = st.selectbox("BHK Config",
        ["1 BHK", "2 BHK", "3 BHK", "4 BHK", "5+ BHK", "Any"], index=2)
    prop_type = st.selectbox("Property Type",
        ["Apartment", "Independent House", "Villa", "Plot"])
    special_reqs = st.text_area("Special Requirements",
        placeholder="e.g. Near Metro, Gated Community, Vastu")

    st.divider()
    st.subheader("🌐 Platforms")
    platforms = []
    if st.checkbox("MagicBricks", value=True):  platforms.append("MagicBricks")
    if st.checkbox("99acres", value=True):       platforms.append("99acres")
    if st.checkbox("Housing.com", value=False):  platforms.append("Housing.com")
    if st.checkbox("NoBroker", value=False):     platforms.append("NoBroker")
    st.caption("💡 Select max 2 to preserve free Firecrawl credits")

# --- Main Header ---
st.title("🏠 Hindustan Realty AI — Investment Advisor")
st.markdown("Multi-agent property search and analysis for the Indian market, powered by **LLaMA 3.3 70B (Groq) + Firecrawl**.")

if not groq_key or not firecrawl_key:
    st.error("⚠️ API keys not configured. Please contact the app owner.")
    st.stop()

if not platforms:
    st.warning("⚠️ Please select at least one platform.")
    st.stop()


# ─── Agent 1: Property Search via Firecrawl ───────────────────────────────────
def run_property_search(city, locality, budget_range, bhk, prop_type, special, platforms):
    fc = Firecrawl(api_key=firecrawl_key)
    city_slug = city.lower().replace(" ", "-")

    urls = []
    if "MagicBricks" in platforms:
        urls.append(f"https://www.magicbricks.com/property-for-sale/residential-real-estate?proptype=Multistorey-Apartment&cityName={city}")
    if "99acres" in platforms:
        urls.append(f"https://www.99acres.com/search/property/buy/{city_slug}")
    if "Housing.com" in platforms:
        urls.append(f"https://housing.com/in/buy/{city_slug}/{city_slug}")
    if "NoBroker" in platforms:
        urls.append(f"https://www.nobroker.in/property/sale/{city_slug}/")

    extract_schema = {
        "type": "object",
        "properties": {
            "properties": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "address":      {"type": "string"},
                        "price_inr":    {"type": "string"},
                        "bhk":          {"type": "string"},
                        "area_sqft":    {"type": "string"},
                        "listing_url":  {"type": "string"},
                        "builder_name": {"type": "string"},
                        "amenities":    {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["address", "price_inr", "bhk", "area_sqft", "listing_url"]
                }
            }
        }
    }

    all_properties = []
    for url in urls[:2]:
        try:
            result = fc.extract(
                urls=[url],
                prompt=(
                    f"Extract all property listings for {bhk} {prop_type} "
                    f"in {locality}, {city}. Budget: ₹{budget_range} Lakhs. "
                    f"Requirements: {special}. "
                    f"For each property get: address, price in INR, BHK config, "
                    f"area in sqft, direct listing URL, builder name, amenities list."
                ),
                schema=extract_schema
            )
            if result and hasattr(result, 'data') and result.data:
                props_raw = result.data.get("properties", [])
                for p in props_raw:
                    try:
                        all_properties.append(PropertyListing(**p))
                    except Exception:
                        pass
        except Exception as e:
            st.warning(f"⚠️ Platform extraction issue: {str(e)[:120]}")
            continue

    # Fallback demo data
    if not all_properties:
        st.info("ℹ️ Live extraction returned no results — showing demo listings.")
        all_properties = [
            PropertyListing(
                address="DLF The Aralias, Golf Course Road, Gurgaon",
                price_inr="12 Cr", bhk="4 BHK", area_sqft="5822",
                listing_url="https://www.magicbricks.com",
                builder_name="DLF", amenities=["Spa", "Gym", "Private Elevator"]
            ),
            PropertyListing(
                address="M3M Golf Estate, Sector 65, Gurgaon",
                price_inr="4.5 Cr", bhk="3 BHK", area_sqft="3000",
                listing_url="https://www.99acres.com",
                builder_name="M3M", amenities=["Golf Course", "Clubhouse", "24/7 Security"]
            ),
            PropertyListing(
                address="SS Highland, Sector 57, Gurgaon",
                price_inr="1.8 Cr", bhk="3 BHK", area_sqft="1800",
                listing_url="https://housing.com",
                builder_name="SS Group", amenities=["Parks", "Parking", "Power Backup"]
            ),
        ]
    return all_properties


# ─── Agent 2: Market Analysis ──────────────────────────────────────────────────
def run_market_analysis(city, listings):
    agent = Agent(
        model=Groq(id="openai/gpt-oss-120b", api_key=groq_key),
        description=f"You are a senior real estate market analyst specializing in {city}, India.",
        instructions=[
            "Give concise, data-driven analysis. Use bullet points.",
            "Always include price-per-sqft benchmarks for the city.",
            "Keep each section under 100 words.",
            "Use INR context throughout (Lakhs, Crores).",
        ],
        markdown=True
    )
    context = f"City: {city}\nListings:\n{json.dumps([l.model_dump() for l in listings], indent=2)}"
    prompt = (
        f"{context}\n\n"
        f"Provide market analysis in this exact format:\n\n"
        f"## 📈 Market Conditions\n"
        f"- Buyer's or Seller's market? Current trend?\n"
        f"- Price per sqft range for this segment\n"
        f"- YoY price change %\n\n"
        f"## 🏘 Neighbourhood Insights\n"
        f"- Key localities and their profiles\n"
        f"- Infrastructure highlights (metro, highways, IT hubs)\n"
        f"- Social infrastructure (schools, hospitals, malls)\n\n"
        f"## 💡 Investment Outlook\n"
        f"- 1–2 year appreciation potential\n"
        f"- Estimated rental yield %\n"
        f"- 2–3 key investment signals\n\n"
        f"## ⚠️ Risk Factors\n"
        f"- Key concerns or red flags for this market"
    )
    response = call_agent_with_retry(agent, prompt)
    return response.content


# ─── Agent 3: Property Valuation ──────────────────────────────────────────────
def run_property_valuation(listings, market_analysis):
    agent = Agent(
        model=Groq(id="openai/gpt-oss-120b", api_key=groq_key),
        description="You are a property valuation expert for Indian real estate.",
        instructions=[
            "Be direct and decisive. No vague language.",
            "Keep each property assessment under 60 words.",
            "Use INR context. Highlight value-for-money clearly.",
        ],
        markdown=True
    )
    props_text = "\n".join([
        f"{i+1}. {p.address} | {p.price_inr} | {p.bhk} | {p.area_sqft} sqft | {p.builder_name}"
        for i, p in enumerate(listings)
    ])
    prompt = (
        f"Market Context:\n{market_analysis}\n\n"
        f"Properties to assess:\n{props_text}\n\n"
        f"For EACH property above provide:\n"
        f"**[Number]. [Address]**\n"
        f"- Valuation: Fair / Overpriced / Underpriced — one reason\n"
        f"- Investment Potential: High / Medium / Low — one reason\n"
        f"- Action: Buy Now / Negotiate / Inspect First / Skip\n\n"
        f"---\n"
        f"## 🏆 Top Pick\n"
        f"Best property from the list and why (2 sentences max).\n\n"
        f"## 🤝 Negotiation Tips\n"
        f"3 specific tactics for this city and budget segment."
    )
    response = call_agent_with_retry(agent, prompt)
    return response.content


# ─── Main Execution ────────────────────────────────────────────────────────────
if st.button("🔍 Search & Analyze Properties", type="primary", use_container_width=True):

    search_criteria = (f"{bhk_config} {prop_type} in {locality}, {city} | "
                       f"₹{min_budget}–{max_budget}L | {special_reqs}")

    # AGENT 1 — Property Search
    with st.status("🚀 Agent 1: Searching properties via Firecrawl...", expanded=True) as status:
        t0 = time.time()
        listings = run_property_search(
            city, locality, f"{min_budget}–{max_budget}",
            bhk_config, prop_type, special_reqs, platforms
        )
        elapsed = round(time.time() - t0, 1)
        st.write(f"✅ Found **{len(listings)}** listings in {elapsed}s")
        status.update(
            label=f"✅ Property Search Complete — {len(listings)} listings ({elapsed}s)",
            state="complete", expanded=False
        )

    if not listings:
        st.error("No listings found. Try adjusting filters.")
        st.stop()

    # Property Cards Grid
    st.subheader(f"🏘 Properties in {locality}, {city}")
    cols = st.columns(3)
    for idx, prop in enumerate(listings):
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(f"**{prop.bhk} — {prop.builder_name or 'Prime Project'}**")
                st.markdown(f"📍 {prop.address}")
                st.markdown(f"<div class='price-tag'>{prop.price_inr}</div>",
                            unsafe_allow_html=True)
                st.markdown(f"📐 {prop.area_sqft} sqft")
                if prop.amenities:
                    st.caption(f"✨ {' · '.join(prop.amenities[:3])}")
                st.link_button("🔗 View Listing", prop.listing_url,
                               use_container_width=True)

    st.divider()

    # AGENT 2 — Market Analysis
    market_md = "Market analysis unavailable."
    with st.status("📊 Agent 2: Analyzing market conditions...", expanded=True) as status:
        t0 = time.time()
        try:
            market_md = run_market_analysis(city, listings)
            elapsed = round(time.time() - t0, 1)
            status.update(label=f"✅ Market Analysis Complete ({elapsed}s)",
                          state="complete", expanded=False)
        except Exception as e:
            st.error(f"Market Analysis failed: {str(e)[:200]}")
            status.update(label="❌ Market Analysis Failed", state="error", expanded=False)

    time.sleep(3)

    # AGENT 3 — Property Valuation
    valuation_md = "Valuation unavailable."
    with st.status("⚖️ Agent 3: Valuing properties...", expanded=True) as status:
        t0 = time.time()
        try:
            valuation_md = run_property_valuation(listings, market_md)
            elapsed = round(time.time() - t0, 1)
            status.update(label=f"✅ Valuations Complete ({elapsed}s)",
                          state="complete", expanded=False)
        except Exception as e:
            st.error(f"Valuation failed: {str(e)[:200]}")
            status.update(label="❌ Valuation Failed", state="error", expanded=False)

    # Results Display
    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📊 Market Analysis")
        st.markdown(market_md)
    with col_b:
        st.subheader("⚖️ Valuations & Recommendations")
        st.markdown(valuation_md)

    # Download Report
    st.divider()
    full_report = f"""# 🏠 Real Estate Analysis Report
**Search:** {search_criteria}
**Generated:** {time.strftime('%d %B %Y, %I:%M %p IST')}

---

## Properties Found ({len(listings)})
{chr(10).join([f"- **{p.address}** | {p.price_inr} | {p.bhk} | {p.area_sqft} sqft | {p.builder_name}" for p in listings])}

---

## Market Analysis
{market_md}

---

## Valuations & Recommendations
{valuation_md}
"""
    st.download_button(
        label="📥 Download Full Report (.md)",
        data=full_report,
        file_name=f"Realty_{city}_{time.strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
        use_container_width=True
    )

# --- Empty State ---
else:
    st.info("👈 Configure your filters in the sidebar and click **Search & Analyze Properties** to begin.")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Agent 1", "Property Search", "Firecrawl Extract API")
    with c2:
        st.metric("Agent 2", "Market Analysis", "LLaMA 3.3 70B via Groq")
    with c3:
        st.metric("Agent 3", "Valuation Engine", "LLaMA 3.3 70B via Groq")
