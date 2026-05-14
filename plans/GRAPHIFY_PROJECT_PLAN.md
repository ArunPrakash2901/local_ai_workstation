# GRAPHIFY PROJECT PLAN
Generated: 2026-05-11

## Candidate Projects on D:\

| # | Project | Indicators | Type | Priority | Safe? | Risk | Notes |
|---|---------|-----------|------|----------|-------|------|-------|
| 1 | **portfolio_website** | npm, git, next, ts, readme | Next.js web app | 🔴 HIGH | ✅ Yes | Low | Active portfolio site. Core product. Graph immediately. |
| 2 | **GSP** | git, R, readme | R project | 🟡 MEDIUM | ✅ Yes | Low | R-based research project. May contain data files (covered by .graphifyignore). |
| 3 | **GSP_2** | R | R project | 🟡 MEDIUM | ✅ Yes | Low | Related R project. Likely continuation of GSP. |
| 4 | **LLM-engineer-handbook** | git, readme | Reference/study | 🟡 MEDIUM | ✅ Yes | Low | Study material / reference repo. Useful for AI context. |
| 5 | **Melbourne-Oil-Scarcity-outlook** | git, readme | Research/analysis | 🟡 MEDIUM | ✅ Yes | Low | Research/analysis project. |
| 6 | **Complete-Data-Science-With-ML-NLP** | git, readme | Study/course | 🟢 LOW | ⚠️ Caution | Medium | Large study repo. May be very noisy with notebooks. Skip .ipynb via ignore. |
| 7 | **kaagle_competitions** | git | Kaggle projects | 🟢 LOW | ⚠️ Caution | Medium | Competition code. May contain data refs. .graphifyignore covers data files. |
| 8 | **Simulation** | git | Code project | 🟢 LOW | ✅ Yes | Low | Unknown purpose. Worth checking size first. |

## Non-Project Folders (Skip)

| Folder | Reason |
|--------|--------|
| graphify-results | Graphify output from prior runs |
| GSP research | No project markers, likely documents |
| MSBA Academic | No project markers, likely documents/coursework |
| Social media | No project markers, likely media/content |
| SteamLibrary | Games folder |
| ollama | Model storage |
| _ai_brain | Our control centre |

## Graphify Execution Plan

### Phase 1: High Priority
1. ✅ `portfolio_website` - Active product, core to career/portfolio

### Phase 2: Medium Priority  
2. `GSP` - R research project
3. `GSP_2` - R research continuation
4. `LLM-engineer-handbook` - AI reference material
5. `Melbourne-Oil-Scarcity-outlook` - Research project

### Phase 3: Low Priority (if Phase 1-2 succeed cleanly)
6. `Simulation` - Check size first
7. `kaagle_competitions` - Check size first
8. `Complete-Data-Science-With-ML-NLP` - Check size first, likely large

## Safety Rules
- Each project graphed individually, never whole D:\
- .graphifyignore in D:\ root covers all projects
- Skip if: >10,000 source files, contains .env files, unclear purpose, huge size
- Successful graphs merged into global graph at D:\_ai_brain\global\
