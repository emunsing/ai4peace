# Adding a scenario

Recommended quickstart/steps for adding a new scenario:

1. Set the scene: what is the historical/geopolitical/social/cultural context, the current situation, and any specific events or changes you want to explore?
2. Choose the characters: choose who is an agent actively making choices in this scene and define their character
3. Configure character details: define their objectives, strategy, and technical capacity--note that these are split into a true/private and (possibly-modified) stated/public view 
4. Add paths or waypoints for the exploration: are there specific external events, known research topics of interest, or other details you wish to observe? Predefine a list of these as choices for the characters/game master

## 1. Set the scene

This is the prompt returned by scenario.get_game_context(self)->str — you'll need to implement this for a new scenario

The current core components of the background/context of a scenario are:
* **Background**: what the simulation seeks to model and why, including a list of most relevant trends, themese, or other context (geopolitics, social/cultural/technological developments, etc)
* **Current situation**: most recent events or developments leading up to the start of the simulation  
* **Key consideration**: a specific element or big change to focus the simulation, such as a recent policy proposal, a major new development or crisis, a global reminder to prioritize cooperative vs competitive aspects, etc.

These aspects are fixed in code for now:
* **Game Mechanics**
* **Victory conditions**
* **Possible actions**

## 2. Choose the characters (agentic roles)

For each character, let's call them Dex, you'll need:

* a name, "Dex"
* a function, `create_dex()` to bundle this together

## 3. Configure character details

* their private vs public information
* each containing objectives, strategy, and assets (technical capacity, capital, and human resources)

## 4. Add paths or waypoints

Generate or manually specify possible anchor branches/events
* research topics
* random events

# Draft MVP

These aspects of the game are currently fixed:
* private vs public info
* Game mechanics 
* Possible actions

## Extension ideas

* character description, backstory, thought processes, etc — some of this may be more inclined towards Concordia

## Conceptual notes

- Current entry point is async def run(self) -> Dict in core/simulation