from dotenv import load_dotenv
import os
import google.generativeai as genai
import streamlit as st
import trafilatura
from trafilatura.metadata import extract_metadata

# --- The functions scrape_article_info, and generate_post_with_gemini remain the same ---
def scrape_article_info(url: str) -> dict:
    """
    Scrape article information from a given URL.
    """
    try:
        html = trafilatura.fetch_url(url)
        if html is None:
            return {"error": "Failed to fetch URL. The link might be broken or the server is blocking requests."}

        content = trafilatura.extract(html, include_comments=False, include_tables=False)
        if not content:
            return {"error": "Failed to extract main content from the page. The page might be heavily JavaScript-based or protected."}

        metadata = extract_metadata(html)
        summary = ' '.join(content.split('.')[:3]).strip() + "."

        return {
            'title': metadata.title if metadata and metadata.title else 'No Title Found',
            'author': metadata.author if metadata and metadata.author else 'Unknown Author',
            'date': metadata.date if metadata and metadata.date else 'Unknown Date',
            'summary': summary,
            'keywords': [],
            'content': content
        }
    except Exception as e:
        return {"error": f"An error occurred during scraping: {e}"}

def generate_post_with_gemini(article_data, tone, audience):
    """
    Generates a LinkedIn post using Google's Gemini model.
    """
    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_NAME"))
    prompt = f"""
    **Your Role:** You are an expert LinkedIn content creator specializing in creating engaging posts for {audience}.
    **Your Task:** Write a LinkedIn post based on the information provided below.
    **Required Tone:** {tone}

    **Instructions:**
    1. Read the provided content.
    2. Create a short, insightful, and engaging LinkedIn post that encourages discussion.
    3. Include 3-5 relevant hashtags at the end.
    4. Do not just summarize. Offer a unique perspective or ask a thought-provoking question.

    ---
    **Title/Topic:** {article_data['title']}
    **Content/Context:**
    {article_data['content'][:4000]}
    ---

    Now, generate the LinkedIn post.
    """
    try:
        response = model.generate_content(prompt)
        if not response.parts:
            return "The model could not generate a response. This might be due to the content policy. Please try a different topic."
        return response.text.strip()
    except Exception as e:
        return f"An error occurred with the Google API: {e}"

# --- Main App Logic ---

# Load environment variables
load_dotenv()
api_key = os.getenv("LLM_API_KEY")
model_name = os.getenv("LLM_MODEL")

# Configure Google AI
if not api_key:
    st.error("Google API Key not found. Please set the GOOGLE_API_KEY in your .env file.")
    st.stop()
genai.configure(api_key=api_key)

# Initialize session state for fallback mechanism
if 'scrape_failed' not in st.session_state:
    st.session_state.scrape_failed = False
    st.session_state.scrape_error_message = ""

# Streamlit UI
st.set_page_config(page_title="LinkedIn Post Generator", layout="centered")
st.title("🤖 AI LinkedIn Post Generator")
st.write("Generate professional LinkedIn posts using Google's Gemini AI. Start with a URL or provide a topic if scraping fails.")

# --- Common Inputs ---
tone = st.selectbox("🎯 Tone", ["Professional", "Inspirational", "Witty", "Casual", "Formal"])
audience = st.text_input("👥 Target Audience", value="AI/ML professionals")
st.markdown("---")


# --- Conditional UI: Show URL input or Fallback input ---

# If scraping has NOT failed, show the URL input field.
if not st.session_state.scrape_failed:
    st.subheader("1. Enter an Article URL")
    url = st.text_input("🔍 URL", placeholder="Paste an article URL here", key="url_input")

    if st.button("🚀 Generate from URL"):
        if url:
            with st.spinner("Scraping article and generating post..."):
                article_data = scrape_article_info(url)
                
                # If scraping fails, set the session state to trigger the fallback UI
                if "error" in article_data:
                    st.session_state.scrape_failed = True
                    st.session_state.scrape_error_message = article_data["error"]
                    st.rerun() # Rerun the script to show the fallback UI immediately
                else:
                    # If scraping succeeds, generate the post
                    result = generate_post_with_gemini(article_data, tone, audience)
                    st.success("✅ Success! Here's your post:")
                    st.text_area("✍️ LinkedIn Post", result, height=250)
        else:
            st.warning("Please enter a URL.")

# If scraping HAS failed, show the fallback UI.
else:
    st.error(f"URL Scraping Failed: {st.session_state.scrape_error_message}")
    st.info("Please provide the topic and a short context manually below.")
    
    st.subheader("2. Or, Provide a Topic Manually")
    
    with st.form("manual_input_form"):
        manual_topic = st.text_input("📝 Topic", placeholder="e.g., The Future of Generative AI")
        manual_context = st.text_area("✍️ Short Context / Key Points", placeholder="e.g., Mention its impact on creative industries, potential for job displacement, and the importance of ethical guidelines.")
        
        submitted = st.form_submit_button("✨ Generate from Topic")

        if submitted:
            if manual_topic and manual_context:
                with st.spinner("Generating post from your topic..."):
                    # Create a dictionary that mimics the structure of article_data
                    manual_article_data = {
                        'title': manual_topic,
                        'content': manual_context
                    }
                    result = generate_post_with_gemini(manual_article_data, tone, audience)
                    st.success("✅ Success! Here's your post:")
                    st.text_area("✍️ LinkedIn Post", result, height=250)
                    
                    # IMPORTANT: Reset the state so the user can try a URL again
                    st.session_state.scrape_failed = False
                    # Add a button to let the user clear the output and start over
                    if st.button("Start Over with a New URL"):
                        st.rerun()
            else:

                st.warning("Please provide both a topic and context.")
