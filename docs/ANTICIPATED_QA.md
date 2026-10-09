# Anticipated Presentation Q&A
## Afterglow — Cross-Domain Entertainment Recommender

Use these as short speaking answers; rephrase them naturally during the presentation.

## Project purpose

### 1. What does your project do?
It brings discovery for movies, series, anime, music, games, novels, and comics into one website. Users can explore popular items or personalize suggestions with their preferred genres and artists.

### 2. What problem does it solve?
Entertainment catalogs are separated across many services. The project gives users one place to browse several media types, narrow results with filters, and follow links to the relevant provider.

### 3. Who is the intended user?
Anyone who wants help finding something to watch, read, play, or listen to—especially someone who wants recommendations across more than one type of entertainment.

### 4. How is it different from a streaming service?
It is a discovery and recommendation interface, not a streaming platform. It gathers catalog information and links users to providers; it does not host movies, books, games, or music.

## Design and implementation

### 5. What technologies did you use?
The frontend uses HTML, CSS, and vanilla JavaScript. The backend uses Python and FastAPI, with HTTPX for external API requests and Pydantic for request validation. Vercel hosts the frontend and Render hosts the API.

### 6. How does a request travel through the system?
The browser calls a FastAPI route. The route selects the relevant provider adapter, which fetches and normalizes catalog data. The backend then adds a recommendation explanation or score when appropriate, and the browser renders the results.

### 7. Why did you use separate APIs for different categories?
Each catalog specializes in a different kind of media. Using TMDB for films and TV, RAWG for games, and book, anime, comics, and music providers gives the application broader catalog coverage without manually maintaining its own database.

### 8. Why FastAPI?
FastAPI makes it straightforward to define typed request models and asynchronous HTTP routes. That fits a backend that spends much of its time waiting for external API responses.

### 9. How does the “For me” mode work?
The browser saves the selected genres and favorite artists locally and sends the relevant preferences with a recommendation request. The backend compares each result's metadata with those preferences, calculates a score, and sorts higher-scoring items first.

### 10. What is the recommendation formula?
The current score adds **3 points per matching preferred genre**, **4 extra points when at least two genres match**, **1.5 points per matching preference/favorite keyword found in the description**, and **5 points if a favorite name appears in the title or credits**. The exact formula is documented in the project report.

### 11. Is this artificial intelligence or machine learning?
Not currently. It is an explainable, rule-based content recommender; it does not train a model or learn from a user's viewing history. A machine-learning approach could be explored later if the project collected suitable consented feedback data.

### 12. How does the system explain a recommendation?
It displays the signal that most strongly supported the match—for example, a favorite artist, a matching genre, or matching description text. If useful metadata is missing, it falls back to a general discovery explanation.

## User experience and results

### 13. What can a user do besides browse?
A user can search within a category, filter by genre or minimum rating, sort by recommendation, rating, or title, reset the filters, open a card for details, and request more results with **Load more**.

### 14. Are filters applied to the entire catalog?
Most search, rating, and sorting controls work on the items currently loaded in the browser. **Load more** adds another provider page. Music genre choices trigger a catalog search; provider metadata may be incomplete, so those results can be less exact than a formal genre-tag filter.

### 15. Does “Load more” mean the list is unlimited?
No. It removes the old one-page display ceiling and continues while the provider reports additional pages. Every upstream catalog still has its own maximum page range, quota, or rate limit.

### 16. Why do ratings sometimes use different scales or disappear?
The catalogs do not use one shared rating system, and some items have no rating. The interface displays a scale based on the available values, but ratings should still be understood in the context of their source.

### 17. Does the Music feature play full songs?
No. When a catalog supplies one, the details dialog can play a short preview. The listening button opens the provider, and **Search on Gaana** opens a Gaana search for the track; the project does not stream full songs itself.

### 18. What happens if an external provider is unavailable?
Some categories have fallbacks: anime can try Jikan when AniList fails, novels can try alternate book catalogs, and Music can fall back to Apple/iTunes on the first page when Deezer is unavailable. If no fallback is available, the app reports an error instead of pretending the result is valid.

## Privacy, testing, and future work

### 19. Where are a user's preferences stored?
In the browser's `localStorage`. The project has no login system or central user database, so preferences stay with that browser and do not automatically sync to another device.

### 20. How are API credentials protected?
Credentials should be stored in backend environment variables, never in frontend code. The current tracked `.env.example` has blank values. Because earlier versions of the public repository may retain committed values in Git history, any real credentials that were previously committed should be revoked or rotated, then updated in Render. No raw keys should be included in a presentation or chat.

### 21. Is the current CORS configuration production-ready?
It currently allows requests from any origin. For a public class demo this is simple, but a production deployment should restrict CORS to the known frontend domain. API credentials remain on the backend rather than being sent to the browser.

### 22. How did you test the project?
I manually checked the main user flows: category loading, preference submission, search, filters, card details, Music links/previews, theme changes, and page-by-page loading. The repository does not yet have a dedicated automated test suite, which is a clear next step.

### 23. What are the main limitations?
The app depends on external APIs, so outages, quotas, and inconsistent metadata affect results. The recommender is rule-based, preferences are browser-specific, Music genre searches depend on provider search quality, and streaming availability hints are not guaranteed real-time checks.

### 24. What would you improve next?
I would add automated tests, restrict CORS, monitor provider failures, improve music genre classification, use a reliable service for current title availability, and optionally learn from user feedback with clear consent.

### 25. What was the most challenging part?
Connecting several unrelated APIs was challenging because every provider returns different fields, pagination rules, and metadata quality. Provider adapters and a common item format make it possible for the frontend to display results consistently.

### 26. What is the strongest design decision in the project?
Keeping provider-specific code behind service adapters while using a common response format. That makes the frontend easier to extend and lets the backend add fallbacks without redesigning every screen.

## Quick demo reminder

1. Show the seven categories and **Explore all**.
2. Demonstrate a genre or rating filter and open a result card.
3. Show the reason, details, and external link.
4. In Music, demonstrate a preview if available and the Gaana search link.
5. Save a preference and switch to **For me**.
6. Use **Load more** to show pagination.
