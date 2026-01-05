from langchain.tools import tool
from tavily import TavilyClient
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize clients
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

@tool
def search_company_overview(company: str) -> str:
    """
    REQUIRED TOOL: Search for company overview and basic information.
    This must be called to understand what the company does.
    """
    try:
        results = tavily.search(
            query=f"{company} company overview business",
            max_results=2
        )
        content = results["results"][0]["content"][:300]
        return f"Overview: {content}"
    except Exception as e:
        return f"Overview: Could not fetch data - {str(e)}"


@tool
def search_stock_price(company: str) -> str:
    """
    REQUIRED TOOL: Search current stock price for the company.
    Must be called before making investment recommendations.
    """
    try:
        results = tavily.search(
            query=f"{company} stock price current today",
            max_results=2
        )
        content = results["results"][0]["content"][:200]
        return f"Stock Price Info: {content}"
    except Exception as e:
        return f"Stock Price Info: Could not fetch data - {str(e)}"


@tool
def search_recent_news(company: str) -> str:
    """
    REQUIRED TOOL: Get recent news about the company.
    Essential for understanding current events affecting the stock.
    """
    try:
        results = tavily.search(
            query=f"{company} latest news recent",
            max_results=3
        )
        news_items = [f"- {r['title']}" for r in results["results"]]
        return "Recent News:\n" + "\n".join(news_items)
    except Exception as e:
        return f"Recent News: Could not fetch data - {str(e)}"


@tool
def search_financial_metrics(company: str) -> str:
    """
    REQUIRED TOOL: Search for financial health indicators.
    Must check financial metrics before investment advice.
    """
    try:
        results = tavily.search(
            query=f"{company} financial metrics revenue profit PE ratio",
            max_results=2
        )
        content = results["results"][0]["content"][:250]
        return f"Financial Metrics: {content}"
    except Exception as e:
        return f"Financial Metrics: Could not fetch data - {str(e)}"


@tool
def analyze_sentiment(news_text: str) -> str:
    """
    OPTIONAL TOOL: Analyze sentiment of news using LLM.
    Helps understand market sentiment but not strictly required.
    """
    prompt = f"""
    Analyze the sentiment of this news about a company:
    {news_text}
    
    Respond with only one word: Positive, Negative, or Neutral
    """
    response = llm.invoke(prompt)
    sentiment = response.content.strip()
    return f"Sentiment Analysis: {sentiment}"


@tool
def generate_report(company: str, collected_data: dict) -> str:
    """
    FINAL TOOL: Generate investment recommendation.
    Should only be called after collecting all required data.
    """
    prompt = f"""
    Create a brief investment analysis for {company} based on:
    
    {collected_data.get('overview', 'NOT PROVIDED')}
    {collected_data.get('price', 'NOT PROVIDED')}
    {collected_data.get('news', 'NOT PROVIDED')}
    {collected_data.get('financials', 'NOT PROVIDED')}
    {collected_data.get('sentiment', 'NOT PROVIDED (optional)')}
    
    Provide:
    1. Brief Summary (2 sentences)
    2. Key Observation
    3. Simple Recommendation
    
    Keep it under 150 words.
    """
    
    response = llm.invoke(prompt)
    return response.content