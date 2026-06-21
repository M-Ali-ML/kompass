# Kompass: The Autonomous AI Travel Architect

## Product Requirements Document (PRD): Kompass Travel Planning App

---

### 1. Product Overview & Objective

The goal of this application is to **automate the overwhelming and manual process of trip planning**.

The app functions as a highly autonomous AI travel assistant (operating at an **8-9 out of 10 autonomy level**) that takes a high-level user prompt and generates a fully integrated, logically optimized itinerary.

---

### 2. Problem Statement

Travelers currently suffer from the "manual labor" of trip planning. Specifically, they struggle with:

* Manually cross-referencing multiple websites to compare prices.
* Determining the best specific dates to travel within a given month.
* Aligning complex logistical schedules, such as ensuring a flight arrival coincides perfectly with a train or ferry departure.

---

### 3. Key Features & Requirements

#### A. Smart Date, Budget & Accommodation Optimization

* **Seasonality Awareness:** The app must identify main, shoulder, and off-seasons for a destination to help users find dates that are less crowded and more budget-friendly.
* **Date Recommendations:** Instead of forcing the user to input specific dates, the app should take broad parameters (e.g., a 10 to 15-day trip in September) and recommend the exact best dates to fly.
* **Live Price Integration:** The application must integrate with live pricing engines (like Google Flights or Skyscanner) to validate recommendations and guarantee the cheapest travel dates.
* **Comprehensive Cost Tracking:** The app must go beyond live flight prices to include accommodation costs, generating subtotals for "Transportation" and "Accommodation" to provide a true Grand Total.
* **Hotel Availability Checking:** The app should track whether user-preferred or highly-rated accommodations are available during the generated dates.

#### B. Intelligent Transportation Logistics

* **Multi-Modal Transport:** The app should support various transportation methods, including flights, trains, and buses, depending on the location.
* **Convenience Filtering:** The system must balance budget with convenience. "Cheapest" should not equal "inconvenient" (e.g., the app should avoid booking flights with three layovers).
* **Detailed Route Sequencing:** The app must handle complex, multi-step routing instructions, such as explicitly noting when a user must *"Fly to Athens and take the first ferry out to Milos."*
* **User Preference Gathering:** The app should ask users for their travel specifications, such as preferred times of day to travel, acceptable journey lengths, or requirements for direct flights.
* **Transit Synchronization:** The app must automatically align connecting travel modes, giving exact times for when a user should take a ferry or train immediately after landing from a flight.

#### C. Scenario Comparison & Scoring

* **Side-by-Side Scenario Generation:** The app must be able to generate and display multiple trip scenarios simultaneously (e.g., comparing an August trip vs. a September trip) in a tabular format, highlighting the price and logistical differences.
* **Qualitative "Stress" Scoring:** Because cheapest does not always mean best, the app should assign a "stress level" or "convenience score" (e.g., 1 to 5) to each itinerary. This score would factor in variables like flight times, the necessity of overnight ferries, and connection tightness.

#### D. Activity & Destination Discovery

* **Vibe-Based Recommendations:** If a user is unfamiliar with a destination's "vibe," the app should ask guiding questions to generate relevant recommendations.
* **Manual Overrides:** Users should be able to explicitly write what they want to do in the prompt if they already know their plans.

> 📌 **Note on Scope:** The app should focus primarily on logistical "heavy lifting." Users often prefer to discover specific day-to-day activities themselves because they know their personal tastes best, so the app shouldn't overly "spoon-feed" sightseeing itineraries unless requested.

#### E. User Interface & Output Formats

* **Visual & Textual Summaries:** The UI must provide a high-level visual summary of the trip.
* **Detailed Views:** The app must also offer detailed text options, including tables, to help the user thoroughly understand the itinerary.

#### F. Session Management & Memory

* **Iterative Workflow:** The app must not force a "single perfect response." It needs to accept ongoing user feedback to tweak parameters and regenerate responses.
* **Trip-Specific Memory:** Users must be able to leave the app and return another day to pick up the conversation exactly where they left off for a specific trip.
* **Global User Profile:** The app must remember the user's general likes and preferences across different trips, applying these learnings as a baseline when a new trip conversation is initiated.
