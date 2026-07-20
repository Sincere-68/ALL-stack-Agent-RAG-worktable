from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from agent.logger.logger import get_logger
from agent.exceptions.custom_exception import CustomException

load_dotenv()
logger = get_logger(__name__)

def get_openai_llm():
    try:
        logger.info("openai LLM invoked")
        
        model = init_chat_model(
            model="gpt-4.1",
            temperature=0
        )
        
        return model
    except Exception as e:
        logger.error("openai LLM failed", exc_info=True)
        raise CustomException(e)

        
    
    

