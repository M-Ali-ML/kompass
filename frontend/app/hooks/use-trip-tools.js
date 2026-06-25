import { useRenderTool } from "@copilotkit/react-core/v2";
import { PreferencesCard, preferencesParameters } from "../components/tool-cards/preferences-card";
import { CheapestDatesCard, cheapestDatesParameters } from "../components/tool-cards/cheapest-dates-card";
import { FlightsCard, flightsParameters } from "../components/tool-cards/flights-card";

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
}
