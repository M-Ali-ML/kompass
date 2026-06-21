"use client";

import React, { useState } from "react";
import ChatPane from "../components/ChatPane";
import { Compass } from "lucide-react";

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
    flights: [
      {
        airline: "Singapore Airlines",
        flight_number: "SQ 938",
        departure_time: "08:20",
        arrival_time: "11:00",
        origin: "SIN",
        destination: "DPS",
        duration_minutes: 160,
        price_usd: 280.0
      }
    ],
    stays: [
      {
        name: "Potato Head Suites",
        location: "Seminyak, Bali",
        check_in: "Day 1",
        check_out: "Day 5",
        rating: 4.8,
        price_per_night_usd: 250.0,
        total_price_usd: 1000.0
      }
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
    flights: [
      {
        airline: "Singapore Airlines",
        flight_number: "SQ 938",
        departure_time: "08:20",
        arrival_time: "11:00",
        origin: "SIN",
        destination: "DPS",
        duration_minutes: 160,
        price_usd: 280.0
      }
    ],
    stays: [
      {
        name: "Ubud Jungle Resort",
        location: "Ubud, Bali",
        check_in: "Day 1",
        check_out: "Day 5",
        rating: 4.7,
        price_per_night_usd: 180.0,
        total_price_usd: 720.0
      }
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
    flights: [
      {
        airline: "Japan Airlines",
        flight_number: "JL 712",
        departure_time: "22:00",
        arrival_time: "06:15",
        origin: "SIN",
        destination: "HND",
        duration_minutes: 435,
        price_usd: 620.0
      }
    ],
    stays: [
      {
        name: "Shibuya Stream Excel Hotel Tokyu",
        location: "Shibuya, Tokyo",
        check_in: "Day 1",
        check_out: "Day 5",
        rating: 4.6,
        price_per_night_usd: 280.0,
        total_price_usd: 1120.0
      }
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
  const [currentDestination, setCurrentDestination] = useState("Bali, Indonesia");
  const [constraints, setConstraints] = useState(["$2500 Budget", "No License", "Vegetarian"]);
  const [activeVibes, setActiveVibes] = useState(["Beach Bliss", "Cultural Immersion"]);
  const [travelers, setTravelers] = useState(2);
  const [isGenerating, setIsGenerating] = useState(false);
  
  const [messages, setMessages] = useState([
    {
      role: "agent",
      content: "Hello! I am Kompass, your autonomous travel planner. I see you want to go to Bali with 2 travelers, a $2500 budget, and no driver's license.\n\nI have generated two distinct travel plans for you: \n\n🌴 **Plan A** focuses on beach clubs, coastal Nusa Penida speedboats, and beach resorts.\n🧘 **Plan B** is a deeply relaxing, cultural retreat in the heart of Ubud's jungles.\n\nSelect a plan below to view details, or ask me to adjust things (e.g. 'Add a surfing lesson on Day 2')",
      scenarios: MOCK_BALI_SCENARIOS
    }
  ]);

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
            flights: sc.flights || [],
            stays: sc.stays || [],
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

          setMessages((prev) => [...prev, {
            role: "agent",
            content: `I've successfully updated your scenarios for ${updatedDestination}! Here are the updated plans.`,
            scenarios: mapped
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
      let mockScenarios = [];
      if (isTokyo) {
        mockScenarios = JSON.parse(JSON.stringify(MOCK_TOKYO_SCENARIOS));
        responseText = "Understood! I've loaded a premium 5-day cyberpunk Tokyo itinerary for you. We'll explore Shibuya Sky, Akihabara gaming arcades, and the breathtaking teamLab Borderless digital arts museum.";
      } else {
        // Just simulate modifying current Bali plan
        mockScenarios = JSON.parse(JSON.stringify(MOCK_BALI_SCENARIOS));
        if (text.toLowerCase().includes("surf") || text.toLowerCase().includes("lesson")) {
          responseText = "Added a custom Private Surf Lesson to Day 2 morning! The stress index remains highly relaxed.";
          if (mockScenarios[0] && mockScenarios[0].days[1]) {
            mockScenarios[0].days[1].activities.unshift({
              id: "b-surf",
              title: "🎓 Added: Private Surf Lesson",
              description: "Learn to catch waves at Double Six Beach with local certified guides.",
              time: "09:00",
              cost_usd: 35
            });
            mockScenarios[0].estimated_cost_usd += 35;
          }
        } else {
          responseText = "Processed your request. I've updated the itinerary details and optimized the pricing breakdown according to your constraints.";
        }
      }

      setMessages((prev) => [...prev, {
        role: "agent",
        content: responseText,
        scenarios: mockScenarios
      }]);
      setIsGenerating(false);
    }, 2500);
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      {/* Minimal Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-surface border-b border-pink-100 pink-shadow shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-primary text-white rounded-2xl bouncy-hover pink-shadow">
            <Compass className="w-6 h-6" />
          </div>
          <span className="text-xl font-bold tracking-tight text-foreground">
            Kompass<span className="text-primary">.ai</span>
            <span className="ml-2 text-xs font-semibold uppercase tracking-widest bg-pink-100 text-primary px-2 py-0.5 rounded-full">
              Agent MVP
            </span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-bold text-muted">Agent System Online</span>
        </div>
      </header>

      {/* Main Workspace Frame - Simplified to only ChatPane */}
      <div className="flex flex-1 overflow-hidden justify-center">
        <div className="w-full max-w-4xl h-full border-x border-pink-100 bg-white">
          <ChatPane 
            messages={messages}
            onSendMessage={handleSendMessage}
            isGenerating={isGenerating}
            activeVibes={activeVibes}
            setActiveVibes={setActiveVibes}
            travelers={travelers}
            setTravelers={setTravelers}
          />
        </div>
      </div>
    </div>
  );
}

