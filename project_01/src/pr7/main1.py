from crewai.flow.flow import Flow, start, listen
from litellm import completion

API_KEY = "AIzaSyAwZkrVp1dvVBqIjqyiNTPGGXP1zgTCVeg"

class CityFunFact(Flow):
    
    @start()
    def generate_random_city(self):
        result = completion(
            model="gemini/gemini-1.5-flash",
            api_key=API_KEY,
            messages=[{"content": "Return any random city name of pakistan", "role": "user"}]
        )
        city = result['choices'][0]['message']['content']
        print(city)
        return city
    
    @listen(generate_random_city)
    def generate_fun_fact(self, city_name):
        result = completion(
            model="gemini/gemini-1.5-flash",
            api_key=API_KEY,
            messages=[{"content": f"Give me a fun fact about {city_name}, Pakistan", "role": "user"}]
        )
        fun_fact = result['choices'][0]['message']['content']
        print(f"Fun fact about {city_name}: {fun_fact}")
        return fun_fact


def kickoff():
    obj = CityFunFact()
    obj.kickoff()


