import { useRenderTool, useHumanInTheLoop } from "@copilotkit/react-core/v2";
import { PreferencesCard, preferencesParameters } from "../components/tool-cards/preferences-card";
import { ClarifyCard, clarifyParameters } from "../components/tool-cards/clarify-card";
import { CheapestDatesCard, cheapestDatesParameters } from "../components/tool-cards/cheapest-dates-card";
import { FlightsCard, flightsParameters } from "../components/tool-cards/flights-card";
import {
  AccommodationsCard,
  accommodationsParameters,
} from "../components/tool-cards/accommodations-card";
import { ResearchCard, researchParameters } from "../components/tool-cards/research-card";
import {
  GroundTransportCard,
  groundTransportParameters,
} from "../components/tool-cards/ground-transport-card";
import {
  ScenarioComparisonCard,
  scenarioComparisonParameters,
} from "../components/tool-cards/scenario-comparison-card";

// Registers the generative-UI renderers for each agent tool. These are hooks,
// so they must be called from a rendered component (here, the page). Add new
// tool cards by registering them alongside the existing ones.
export function useTripTools() {
  useRenderTool({
    name: "gather_preferences",
    parameters: preferencesParameters,
    render: (props) => <PreferencesCard {...props} />,
  });

  useRenderTool({
    name: "find_cheapest_dates",
    parameters: cheapestDatesParameters,
    render: (props) => <CheapestDatesCard {...props} />,
  });

  useRenderTool({
    name: "search_flights",
    parameters: flightsParameters,
    render: (props) => <FlightsCard {...props} />,
  });

  useRenderTool({
    name: "search_accommodations",
    parameters: accommodationsParameters,
    render: (props) => <AccommodationsCard {...props} />,
  });

  useRenderTool({
    name: "search_web",
    parameters: researchParameters,
    render: (props) => <ResearchCard {...props} />,
  });

  useRenderTool({
    name: "search_ground_transport",
    parameters: groundTransportParameters,
    render: (props) => <GroundTransportCard {...props} />,
  });

  useRenderTool({
    name: "generate_scenarios",
    parameters: scenarioComparisonParameters,
    render: (props) => <ScenarioComparisonCard {...props} />,
  });

  // Human-in-the-loop: the agent calls this when it needs more info. The run
  // pauses on the card until the traveler picks an option or types an answer
  // (respond), then resumes. Defined as a frontend tool, so PydanticAI's AG-UI
  // adapter exposes it to the agent automatically — no backend tool code.
  useHumanInTheLoop({
    name: "ask_clarifying_question",
    description:
      "Ask the traveler ONE focused clarifying question when required trip info is " +
      "missing or ambiguous. Provide 2-4 concrete `options`; the traveler may also " +
      "type a free-text answer. Set `allow_multiple` when several options can be " +
      "chosen. Returns the traveler's answer as text.",
    parameters: clarifyParameters,
    render: (props) => <ClarifyCard {...props} />,
  });
}
