"use client";

import React, { useState } from "react";
import TopAppBar from "../components/TopAppBar";
import LeftSidebar from "../components/LeftSidebar";
import ChatPane from "../components/ChatPane";
import LiveTimeline from "../components/LiveTimeline";
import MapDrawer from "../components/MapDrawer";
import ComparisonDashboard from "../components/ComparisonDashboard";

// Pre-packaged Mock Scenarios for Bali and Tokyo for immediate interaction & API offline fallback
const MOCK_BALI_SCENARIOS = [
  {
    id: "bali-beach-bliss",
    title: "🌴 Plan A: Seminyak Beach Bliss & Nusa Penida",
    destination: "Bali, Indonesia",
    duration_days: 5,
    estimated_cost_usd: 2150,
    stress_score: 2,
    highlights: [
      "5-star beach resort stay in vibrant Seminyak",
      "Private speedboat day-trip to Nusa Penida highlights",
      "Sunset seafood dinner at Jimbaran beach",
      "VIP daybed at Potato Head Beach Club"
    ],
    days: [
      {
        day_number: 1,
        title: "Beachfront Arrival & Sunset Vibe",
        activities: [
          { id: "b1", title: "Resort Check-In", description: "Arrive at Potato Head Suites Seminyak, check in and receive welcome drink.", time: "14:00", cost_usd: 0 },
          { id: "b2", title: "Jimbaran Sunset Seafood Dinner", description: "Freshly grilled snapper and clams directly on the sand as the sun goes down.", time: "18:00", cost_usd: 65 }
        ]
      },
      {
        day_number: 2,
        title: "Surfing & Beach Clubs",
        activities: [
          { id: "b3", title: "Private Surf Lesson", description: "Learn to catch waves at Double Six Beach with local certified guides.", time: "09:00", cost_usd: 35 },
          { id: "b4", title: "Potato Head VIP Daybed", description: "Lounge by the infinity pool, sip signature cocktails and enjoy beachfront tunes.", time: "14:00", cost_usd: 120 }
        ]
      },
      {
        day_number: 3,
        title: "Nusa Penida Coastal Adventure",
        activities: [
          { id: "b5", title: "Speedboat to Nusa Penida", description: "Cross the strait from Sanur harbor to Penida island.", time: "07:30", cost_usd: 40 },
          { id: "b6", title: "Kelingking Beach hike", description: "Witness the iconic T-Rex shaped cliff view and climb down to the pristine sand.", time: "10:00", cost_usd: 15 }
        ]
      },
      {
        day_number: 4,
        title: "Chilled Spa & Shopping",
        activities: [
          { id: "b7", title: "Balinese Luxury Spa Session", description: "2-hour full body oil massage and flower bath.", time: "11:00", cost_usd: 50 },
          { id: "b8", title: "Seminyak Boutique Shopping", description: "Stroll through design boutiques and pick up handmade clothing.", time: "15:00", cost_usd: 80 }
        ]
      },
      {
        day_number: 5,
        title: "Final Dip & Departure",
        activities: [
          { id: "b9", title: "Morning beach yoga", description: "Gentle sunrise stretch on Seminyak beach.", time: "07:00", cost_usd: 15 },
          { id: "b10", title: "Airport Transfer", description: "Private shuttle back to Denpasar Airport for departure.", time: "12:00", cost_usd: 20 }
        ]
      }
    ]
  },
  {
    id: "bali-cultural-escape",
    title: "🧘 Plan B: Ubud Cultural & Jungle Sanctuary",
    destination: "Bali, Indonesia",
    duration_days: 5,
    estimated_cost_usd: 1850,
    stress_score: 1,
    highlights: [
      "Jungle villa stay with private plunge pool",
      "Purification ritual water blessing at Tirta Empul",
      "Traditional Balinese cooking class in organic garden",
      "Sunrise trekking at Tegalalang Rice Terraces"
    ],
    days: [
      {
        day_number: 1,
        title: "Jungle Sanctuary Check-in",
        activities: [
          { id: "u1", title: "Check-in at Ubud Jungle Resort", description: "Settle into a private pool villa overlooking the Ayung River.", time: "14:00", cost_usd: 0 },
          { id: "u2", title: "Welcome Dinner", description: "Organic farm-to-table Balinese dining under the stars.", time: "19:00", cost_usd: 40 }
        ]
      },
      {
        day_number: 2,
        title: "Tegalalang Rice Walk & Holy Spring",
        activities: [
          { id: "u3", title: "Tegalalang Sunrise Walk", description: "Walk through the stunning green cascading rice terraces at cool early morning.", time: "06:30", cost_usd: 10 },
          { id: "u4", title: "Tirta Empul Water Blessing", description: "Participate in a spiritual purification ritual at the sacred hot spring pools.", time: "10:30", cost_usd: 25 }
        ]
      },
      {
        day_number: 3,
        title: "Monkeys & Dance",
        activities: [
          { id: "u5", title: "Sacred Monkey Forest Sanctuary", description: "Observe Balinese long-tailed macaques in their jungle habitat.", time: "10:00", cost_usd: 12 },
          { id: "u6", title: "Kecak Fire Dance Performance", description: "Traditional music and dance storytelling at Ubud Palace.", time: "19:00", cost_usd: 20 }
        ]
      },
      {
        day_number: 4,
        title: "Culinary Class & Art",
        activities: [
          { id: "u7", title: "Balinese Cooking Class", description: "Gather fresh ingredients in the market and learn to cook 5 traditional dishes.", time: "09:00", cost_usd: 45 },
          { id: "u8", title: "Ubud Art Market stroll", description: "Bargain for gorgeous handmade straw bags, paintings, and wood carvings.", time: "15:00", cost_usd: 30 }
        ]
      },
      {
        day_number: 5,
        title: "Yoga & Farewell",
        activities: [
          { id: "u9", title: "Yoga class at Yoga Barn", description: "Relaxing Vinyasa flow session in the iconic wooden shala.", time: "08:00", cost_usd: 12 },
          { id: "u10", title: "Transfer to Airport", description: "Head back to the airport with fresh memories.", time: "13:00", cost_usd: 25 }
        ]
      }
    ]
  }
];

const MOCK_TOKYO_SCENARIOS = [
  {
    id: "tokyo-neon-cyber",
    title: "🤖 Plan A: Shibuya Neon Nights & Cyberpunk Tokyo",
    destination: "Tokyo, Japan",
    duration_days: 5,
    estimated_cost_usd: 2950,
    stress_score: 3,
    highlights: [
      "Stay in the heart of Shibuya neon district",
      "Akihabara retro gaming & maid cafe tour",
      "Digital art immersive ticket to teamLab Borderless",
      "Shibuya Crossing sky-deck sunset view"
    ],
    days: [
      {
        day_number: 1,
        title: "Welcome to Tokyo Cyber City",
        activities: [
          { id: "t1", title: "Shibuya Hotel Check-In", description: "Check in at Shibuya Stream Excel Hotel.", time: "15:00", cost_usd: 0 },
          { id: "t2", title: "Shibuya Sky Sunset", description: "Observe Tokyo's skyline and Shibuya crossing from 229m in the air.", time: "18:00", cost_usd: 22 }
        ]
      },
      {
        day_number: 2,
        title: "Subculture & Immersive Art",
        activities: [
          { id: "t3", title: "teamLab Borderless Museum", description: "Stroll through jaw-dropping interactive digital projection rooms.", time: "10:00", cost_usd: 35 },
          { id: "t4", title: "Harajuku Takeshita Street", description: "Try colorful rainbow cotton candy and shop for quirky fashion items.", time: "14:00", cost_usd: 20 }
        ]
      },
      {
        day_number: 3,
        title: "Otaku & Retro Arcades",
        activities: [
          { id: "t5", title: "Akihabara Cyber Tour", description: "Visit Super Potato for retro games and explore mega stores.", time: "11:00", cost_usd: 40 },
          { id: "t6", title: "Golden Gai bar hopping", description: "Cozy drinks in tiny historic alleys of Shinjuku.", time: "20:00", cost_usd: 60 }
        ]
      },
      {
        day_number: 4,
        title: "Anime & Gaming",
        activities: [
          { id: "t7", title: "Ghibli Museum Visit", description: "Explore the magical world of Hayao Miyazaki animation.", time: "10:00", cost_usd: 15 },
          { id: "t8", title: "Odaiba Gundam & Joypolis", description: "See the giant unicorn Gundam and play inside Sega's indoor theme park.", time: "14:30", cost_usd: 50 }
        ]
      },
      {
        day_number: 5,
        title: "Farewell Tokyo",
        activities: [
          { id: "t9", title: "Meiji Shrine Morning Walk", description: "Peaceful forest walk to the majestic Shinto shrine.", time: "09:00", cost_usd: 0 },
          { id: "t10", title: "Narita Express Transfer", description: "Bullet-shuttle back to airport.", time: "13:00", cost_usd: 30 }
        ]
      }
    ]
  }
];

export default function Home() {
  const [activeTab, setActiveTab] = useState("chat");
  const [currentDestination, setCurrentDestination] = useState("Bali, Indonesia");
  const [constraints, setConstraints] = useState(["$2500 Budget", "No License", "Vegetarian"]);
  const [activeVibes, setActiveVibes] = useState(["Beach Bliss", "Cultural Immersion"]);
  const [travelers, setTravelers] = useState(2);
  const [savedAssets, setSavedAssets] = useState([]);
  const [isMapOpen, setIsMapOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  
  const [itineraries, setItineraries] = useState(MOCK_BALI_SCENARIOS);
  const [activeItineraryId, setActiveItineraryId] = useState("bali-beach-bliss");
  
  const [messages, setMessages] = useState([
    {
      role: "agent",
      content: "Hello! I am Kompass, your autonomous travel planner. I see you want to go to Bali with 2 travelers, a $2500 budget, and no driver's license.\n\nI have generated two distinct travel plans for you: \n\n🌴 **Plan A** focuses on beach clubs, coastal Nusa Penida speedboats, and beach resorts.\n🧘 **Plan B** is a deeply relaxing, cultural retreat in the heart of Ubud's jungles.\n\nSelect a scenario on the right or ask me to adjust things (e.g. 'Add a surfing lesson on Day 2')",
      widget: "vibe_selector"
    }
  ]);

  const activeItinerary = itineraries.find((p) => p.id === activeItineraryId) || itineraries[0];

  const handleSendMessage = async (text) => {
    // 1. Add User Message
    const newMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, newMsg]);
    setIsGenerating(true);

    // Update state based on keywords
    let updatedDestination = currentDestination;
    let isTokyo = false;
    if (text.toLowerCase().includes("tokyo") || text.toLowerCase().includes("japan")) {
      updatedDestination = "Tokyo, Japan";
      setCurrentDestination("Tokyo, Japan");
      isTokyo = true;
    }

    // 2. Perform API Call to backend with fallback
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          session_id: "demo-session"
        })
      });

      if (response.ok) {
        const data = await response.json();
        const payload = data.response; // ScenarioMatrix
        if (payload && payload.scenarios && payload.scenarios.length > 0) {
          // Map backend Scenarios to frontend
          const mapped = payload.scenarios.map((sc, idx) => ({
            id: sc.scenario_id || `plan-${idx}`,
            title: sc.title || `Plan ${idx + 1}`,
            destination: updatedDestination,
            duration_days: sc.itinerary?.length || 5,
            estimated_cost_usd: sc.grand_total_usd || 1500,
            stress_score: sc.stress_score || 2,
            highlights: sc.summary ? [sc.summary] : ["AI Generated travel itinerary"],
            days: sc.itinerary?.map((day) => ({
              day_number: day.day_number,
              title: day.title || `Day ${day.day_number}`,
              activities: day.activities?.map((act, actIdx) => ({
                id: `act-${day.day_number}-${actIdx}`,
                title: act.name || act.title,
                description: act.description,
                time: act.start_time || "10:00",
                cost_usd: act.cost_usd || 0
              }))
            })) || []
          }));

          setItineraries(mapped);
          setActiveItineraryId(mapped[0].id);
          setMessages((prev) => [...prev, {
            role: "agent",
            content: `I've successfully updated your scenarios for ${updatedDestination}! Here are the updated plans.`,
            widget: "traveler_counter"
          }]);
          setIsGenerating(false);
          return;
        }
      }
    } catch (err) {
      console.warn("API Offline, falling back to local simulation.", err);
    }

    // 3. Fallback Local Simulation
    setTimeout(() => {
      let responseText = "";
      if (isTokyo) {
        setItineraries(MOCK_TOKYO_SCENARIOS);
        setActiveItineraryId("tokyo-neon-cyber");
        responseText = "Understood! I've loaded a premium 5-day cyberpunk Tokyo itinerary for you. We'll explore Shibuya Sky, Akihabara gaming arcades, and the breathtaking teamLab Borderless digital arts museum.";
      } else {
        // Just simulate modifying current Bali plan
        const updated = [...itineraries];
        if (text.toLowerCase().includes("surf") || text.toLowerCase().includes("lesson")) {
          responseText = "Added a custom Private Surf Lesson to Day 2 morning! The stress index remains highly relaxed.";
          // Update surf activity
          if (updated[0] && updated[0].days[1]) {
            updated[0].days[1].activities.unshift({
              id: "b-surf",
              title: "🎓 Added: Private Surf Lesson",
              description: "Learn to catch waves at Double Six Beach with local certified guides.",
              time: "09:00",
              cost_usd: 35
            });
            updated[0].estimated_cost_usd += 35;
          }
        } else {
          responseText = "Processed your request. I've updated the itinerary details and optimized the pricing breakdown according to your constraints.";
        }
        setItineraries(updated);
      }

      setMessages((prev) => [...prev, {
        role: "agent",
        content: responseText,
        widget: isTokyo ? "traveler_counter" : "vibe_selector"
      }]);
      setIsGenerating(false);
    }, 2500);
  };

  const handleNewTrip = () => {
    setMessages([]);
    setSavedAssets([]);
    setConstraints(["$2500 Budget"]);
    setActiveVibes([]);
    setTravelers(1);
    setItineraries([]);
  };

  const handleSearchDestination = (val) => {
    setCurrentDestination(val);
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Navbar */}
      <TopAppBar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab}
        currentDestination={currentDestination}
        onSearchDestination={handleSearchDestination}
      />

      {/* Main Workspace Frame */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Control Panel */}
        <LeftSidebar 
          constraints={constraints}
          setConstraints={setConstraints}
          savedAssets={savedAssets}
          setSavedAssets={setSavedAssets}
          onNewTrip={handleNewTrip}
        />

        {/* Content Pane Switcher */}
        {activeTab === "chat" ? (
          <div className="flex flex-1 overflow-hidden">
            {/* Center Chat Dialog */}
            <ChatPane 
              messages={messages}
              onSendMessage={handleSendMessage}
              isGenerating={isGenerating}
              activeVibes={activeVibes}
              setActiveVibes={setActiveVibes}
              travelers={travelers}
              setTravelers={setTravelers}
            />

            {/* Right Live Itinerary Timeline */}
            <LiveTimeline 
              itinerary={activeItinerary}
              savedAssets={savedAssets}
              setSavedAssets={setSavedAssets}
              onToggleMap={() => setIsMapOpen(true)}
              isMapOpen={isMapOpen}
            />
          </div>
        ) : (
          /* Comparison matrix dashboard */
          <ComparisonDashboard 
            itineraries={itineraries}
            activeItineraryId={activeItineraryId}
            onSelectActive={(id) => {
              setActiveItineraryId(id);
              setActiveTab("chat"); // Return to chat focus
            }}
          />
        )}
      </div>

      {/* Interactive Map Drawer (FAB toggle) */}
      <MapDrawer 
        isOpen={isMapOpen}
        onClose={() => setIsMapOpen(false)}
        destination={currentDestination}
        itinerary={activeItinerary}
      />
    </div>
  );
}
