# ForkCaster: Finding the Right Place for the Right Moment

## The Project

My agent chatbot, ForkCaster, is an AI-powered restaurant and food recommendation assistant designed to help users find places to eat based on their specific needs and preferences. The agent solves a decision paralysis problem that is quite simple yet exhaustive: where should I eat today? As someone that gets overwhelmed with the number of choices of restaurants, bakeries, and coffee shops offered in NYC, this chatbot can provide the user a simple condensed solution recommending locations that are best suited for user's needs. The agent I built uses OpenStreetMap data to convert location names into coordinates and identify real restaurants and food establishments in the area requested. OpenStreetMap provides a variety of attributes, including cuisine type, opening hours, outdoor seating, Wi-Fi availability, and more, allowing the chatbot to generate recommendations based on a multitude of criteria (if publicly available).

Beyond basic location-based search, the chatbot personalizes recommendations based on the user’s inputted occasion. Users can search for places suited for date nights, study sessions, large groups, milestone celebrations, casual meals, and other occasions to personalize their food recommendations even further. Each occasion is scored using a unique combination of factors, including walkability, accessibility, reservation requirements, and internet availability, with different weights based on the needs of the occasion. By combining geographic data, restaurant attributes, and contextual preferences, the agent can identify and recommend real locations that best fit the user's specific occasion.

URL: https://forkcaster-git-708411086094.europe-west1.run.app

## Tools Implemented
Name and describe your tools and their arguments well and gracefully handle errors relaying actionable information to the model

### `geocode_location`
 Using the Open Street Map data, it intakes a place name or address as a String and returns its coordinates. If it can't find a specific name, it may prompt to be more specific of the location using a city or state.
  - **Arguments:** place name (str)

### `search_places` *(Tool Requesting External API)*
 Using the Open Street Map data to find nearby restaurants by the type of category and cuisine a user requests and returns details of the restaurant such as distance, address, opening hours, outdoor seating availability, internet access, cuisine, reservation requirements, etc. The tool takes the latitude and longitude of a specific area, restaurant category, cuisine type, and desired search radius as inputs. This location-based restaurant search tool allows the user to customize its requests by typical criterias used to find restaurants and enables the chatbot to scrape and personalize its recommendation to the users criteria
  - **Arguments:** latitude, longitude, category, radius, cuisine

### `get_occasion_profile` *(original)*
 Translates a user’s occasion, group size, duration, and weather into weighted recommendation criteria and suggested place categories for the chatbot to weigh out its recommendations
 - **Arguments:** occasion, group size, duration, weather

### `score_places_for_occasion` *(original)*
 This tool ranks places from 0-100 based on how well they match the user's preferences in ocassion, group size, durations (as input arguments). It also considers whether a location has any unknown information as part of the criteria (assigning partial credit for when the data is unavailable) and ranks each of its selected locations by score, confidence and distance. 
 - **Arguments:** places, occasion, group size, duration, weather



## Helper Functions 

### `distance_m`
 Calculates distances between two coordinates using their latitutde and longitude (arguments)
  - **Arguments:** latitude, longitude

### `normalize_occasions` 
 Converts our options of occassions (such as date night, large party, study / work spot, etc) into a list format
  - **Arguments:** occassions

### `build_profile`
 Profile-building tool that converts the user’s occasion, party size, visit duration, and weather conditions into weighted recommendation criteria that can be dynamically adjusted to prioritize Wi-Fi for longer visits or indoor spaces on rainy days. 
  - **Arguments:** occasions, party size, duration, weather

### `eval_criterion`
 Recommendation filtering tool that evaluates restaurants against user preferences—such as walkability, Wi-Fi, outdoor seating, indoor space, wheelchair accessibility, large-party capacity, and reservations—and identifies whether each criterion is met, unmet, or unknown based on available OpenStreetMap data. 
  - **Arguments:** name, place, profile


## Sample Queries to Test With

### Query 1: First date in the East Village
> I have a first date next weekend in the East Village, provide me restaurant recommendations with outdoor seating for this occasion.

**Follow-ups:**
1. I am only interested in Italian food, update your recommendations and explain how you'd rank them for a date?
2. Of these options, I'm more inclined towards the 2nd option, help me find a dessert location for after dinner.
3. What's a nice bar within a 10 minute walk that we can go to afterwards?


### Query 2: Japanese food in the Lower East Side
> I am craving Japanese food that is at most a 15 minute walk in the Lower East Side. I'm planning to take my family of 5 and we'd prefer no reservation requirements.

**Follow-ups:**
1. I am planning on an early dinner, what are the top 3 best options?
2. Will I need a reservation for the second option? If so what are other recommendations without a reservation

### Query 3: Food crawl in Chinatown
> I am planning a food crawl in Chinatown NYC, can you give me a couple of recommendations of where to go?

**Follow-ups:**
1. How close are these spots from each other? Could you provide me an itinerary for my food crawl?
2. What food spots should we prioritize based on the current weather?

### Query 4: Study session near Columbia
> What is the closest coffee shop near Columbia University for a study session?

**Follow-ups:**
1. Are there any coffee shops that offer confirmed internet access? I am willing to walk a bit further if so.
2. Are there any bakeries nearby where I could grab a sweet treat afterwards?
