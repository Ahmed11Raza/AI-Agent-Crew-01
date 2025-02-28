from crewai.flow.flow import Flow, start, listen
import random

class RouteFlow(Flow):
    
    @start()  # Need parentheses here
    def greeting(self):
        print("hello!")
        return "greeting completed"  # Need to return a value for the next step to listen to
    
    @listen(greeting)
    def select_city(self, greeting_result):  # Should accept the result from the previous step
        cities = ["Karachi", "Islamabad", "Lahore"]
        selected_city = random.choice(cities)
        print(selected_city)
        return selected_city
        
def kickoff():
    flow = RouteFlow()
    flow.kickoff()  # Method should be kickoff() not start()

if __name__ == "__main__":
    kickoff()