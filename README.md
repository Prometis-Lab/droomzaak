<p align="center">
  <img src="droomzaak.png" alt="droomzaak" width="280">
</p>

<h1 align="center">droomzaak</h1>

<p align="center"><em>Van droom tot zaak.</em></p>

---

An interactive map for aspiring entrepreneurs in Ghent. Start from a dream — an idea, a craft, a thing you've always wanted to build — drop it on a spot, and the city responds. Live data layers light up: who your competitors are, who lives in the catchment, what drives footfall, how far people can walk to you. An agent reasons over all of it and answers your questions in plain language — *"where could this actually work?"* — then hands you a one-page starter dossier and routes you to the partners who actually help you found the company.

Built by [Prometis Lab](https://prometislab.org) for the Hackers & Ravers company cup, aligned with the Stad Gent / District09 XpertFinder one-stop-shop-for-starters challenge.

## The idea in one flow

1. *Dream* — bring your idea, drop a pin. The map responds.
2. *Compare* — competitors, catchment, income, footfall, 10-minute walking reach overlay on the map.
3. *Ask* — natural-language queries answered by an agent over the data layers, with reasoning ("low bakery density, high income, strong footfall here").
4. *Commit* — generate a starter dossier for the chosen spot.
5. *Route* — the dossier deep-links into existing services for registration, permits and funding. Droomzaak decides which services you need and hands you off with context pre-filled.

## Setup

After cloning, point git at the shared hooks directory once:

```sh
git config core.hooksPath .githooks
```