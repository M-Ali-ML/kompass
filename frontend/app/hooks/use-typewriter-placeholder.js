"use client";

import { useEffect, useState } from "react";

// Rotating placeholder prompts that cycle through the chat input to give the
// user ideas of what to ask for. Each is "typed in" then "typed out" with a
// blinking caret for an appealing animation.
export const PLACEHOLDER_PROMPTS = [
  "Help me plan a trip to Japan",
  "Berlin to Italy vacation plan",
  "A week of island hopping in Greece",
  "Weekend getaway from Paris",
  "Plan a road trip along the California coast",
  "Romantic 5-day trip to Lisbon",
  "Backpacking route through Southeast Asia",
  "Family-friendly holiday in Costa Rica",
  "Ski trip to the Swiss Alps",
  "Foodie tour of Tokyo and Osaka",
  "Northern Lights adventure in Iceland",
  "Cultural city break in Istanbul",
];

// Typewriter timing (ms). Type-in is a touch slower than delete so reading the
// full prompt feels natural; the long hold lets the user actually read it.
const TYPE_IN_MS = 55;
const TYPE_OUT_MS = 28;
const HOLD_FULL_MS = 1800;
const HOLD_EMPTY_MS = 450;
const CARET_BLINK_MS = 500;

// Drives a typewriter animation over `prompts`, returning the current partial
// string to use as a placeholder. It types a prompt in char-by-char, holds it,
// deletes it, then advances to the next — looping forever. A trailing caret
// ("│") is appended so the placeholder reads like a live cursor is typing.
export function useTypewriterPlaceholder(prompts) {
  const [text, setText] = useState("");
  const [caretOn, setCaretOn] = useState(true);

  useEffect(() => {
    let promptIndex = 0;
    let charIndex = 0;
    let deleting = false;
    let timer;

    const tick = () => {
      const full = prompts[promptIndex];
      charIndex += deleting ? -1 : 1;
      setText(full.slice(0, charIndex));

      let delay;
      if (!deleting && charIndex === full.length) {
        // Finished typing in — hold the full prompt, then start deleting.
        deleting = true;
        delay = HOLD_FULL_MS;
      } else if (deleting && charIndex === 0) {
        // Finished deleting — advance to the next prompt after a short beat.
        deleting = false;
        promptIndex = (promptIndex + 1) % prompts.length;
        delay = HOLD_EMPTY_MS;
      } else {
        delay = deleting ? TYPE_OUT_MS : TYPE_IN_MS;
      }
      timer = setTimeout(tick, delay);
    };

    timer = setTimeout(tick, TYPE_IN_MS);
    return () => clearTimeout(timer);
  }, [prompts]);

  // Blink the caret independently so it keeps pulsing during the read holds,
  // not just while characters are being added/removed.
  useEffect(() => {
    const id = setInterval(() => setCaretOn((on) => !on), CARET_BLINK_MS);
    return () => clearInterval(id);
  }, []);

  // The caret is part of the placeholder string; swap a thin space in when
  // "off" so the text width stays put and the caret simply blinks in place.
  return `${text}${caretOn ? "│" : "\u2009"}`;
}
