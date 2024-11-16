import tiktoken

class CostCalculator:
    def __init__(self):
        """
        מחשבון עלויות לשימוש ב-Azure OpenAI
        """
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        self.prices = {
            'gpt-4': {
                'input': 0.03,   # $0.03 per 1K tokens
                'output': 0.06   # $0.06 per 1K tokens
            }
        }

    def estimate_tokens(self, text: str) -> int:
        """
        הערכת מספר הטוקנים בטקסט
        """
        return len(self.encoding.encode(text))

    def calculate_cost(self, input_tokens: int, output_tokens: int = None, model: str = 'gpt-4') -> dict:
        """
        חישוב העלות המשוערת
        """
        if output_tokens is None:
            output_tokens = input_tokens // 2  # הערכה גסה לגודל התשובה

        input_cost = (input_tokens / 1000) * self.prices[model]['input']
        output_cost = (output_tokens / 1000) * self.prices[model]['output']
        total_cost = input_cost + output_cost

        return {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'input_cost': input_cost,
            'output_cost': output_cost,
            'total_cost': total_cost
        }