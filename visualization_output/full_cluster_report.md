# Documentation Feedback Clustering Analysis Report

Generated: 2025-07-02 21:06:01

## Executive Summary

This report presents the results of clustering analysis performed on **4,926 documentation feedback entries** collected from various programs. The analysis used advanced natural language processing techniques to identify patterns and group similar feedback together.

## Dataset Overview

- **Total Entries:** 4,926
- **Number of Clusters:** 2
- **Date Range:** 2018-10-24 15:51:54.359283+00 to 2025-07-02 18:58:46.735252+00
- **Programs Represented:** 24

## Clustering Results

The clustering algorithm identified **2 distinct clusters** in the feedback data:


### Cluster 0

- **Size:** 24 entries (0.5% of total)
- **Date Range:** 2019-10-19 02:05:51.790623+00 to 2024-01-09 22:11:40.963394+00

#### Program Distribution in Cluster 0

| Program | Count | Percentage |
|---------|-------|------------|
| Chicago | 14 | 58.3% |
| Cleveland | 10 | 41.7% |

#### Sample Entries from Cluster 0

**Entry 1920** (Program: Chicago)
- **Issue:** https://twitter.com/KateLinderman4/status/1716831491630760429
- **What was hard:** https://twitter.com/KateLinderman4/status/1716831491630760429

**Entry 1948** (Program: Cleveland)
- **Issue:** Here’s the link to my Twitter thread: https://x.com/rosiepalfy/status/1713979214720840050?s=61&t=ENZbU3JWE-BEYTmNBNHYJA
- **What was hard:** Here’s the link to my Twitter thread: https://x.com/rosiepalfy/status/1713979214720840050?s=61&t=ENZbU3JWE-BEYTmNBNHYJA

**Entry 1876** (Program: Chicago)
- **Issue:** https://twitter.com/KateLinderman4/status/1721602727153745998
- **What was hard:** https://twitter.com/KateLinderman4/status/1721602727153745998

**Entry 3686** (Program: Cleveland)
- **Issue:** Twitter thread:
https://twitter.com/whatuphails/status/1372653034065510411?s=20
- **What was hard:** Twitter thread:
https://twitter.com/whatuphails/status/1372653034065510411?s=20

**Entry 3672** (Program: Cleveland)
- **Issue:** https://twitter.com/whatuphails/status/1375203666530086913?s=20
- **What was hard:** https://twitter.com/whatuphails/status/1375203666530086913?s=20


### Cluster 1

- **Size:** 4,902 entries (99.5% of total)
- **Date Range:** 2018-10-24 15:51:54.359283+00 to 2025-07-02 18:58:46.735252+00

#### Program Distribution in Cluster 1

| Program | Count | Percentage |
|---------|-------|------------|
| Chicago | 1765 | 36.0% |
| Detroit | 1057 | 21.6% |
| Cleveland | 657 | 13.4% |
| Indianapolis | 214 | 4.4% |
| Minneapolis | 205 | 4.2% |
| Akron | 174 | 3.5% |
| Philadelphia | 167 | 3.4% |
| Atlanta | 135 | 2.8% |
| Omaha | 106 | 2.2% |
| Wichita | 92 | 1.9% |
| San Diego | 75 | 1.5% |
| Dallas | 74 | 1.5% |
| Grand Rapids | 41 | 0.8% |
| Fresno | 31 | 0.6% |
| Bismarck | 20 | 0.4% |
| Cincinnati | 16 | 0.3% |
| Los Angeles | 14 | 0.3% |
| Columbia Gorge | 13 | 0.3% |
| Spokane | 12 | 0.2% |
| Fort Worth | 11 | 0.2% |
| New Brunswick | 11 | 0.2% |
| Newark | 9 | 0.2% |
| Tulsa | 2 | 0.0% |
| Centre County | 1 | 0.0% |

#### Sample Entries from Cluster 1

**Entry 3833** (Program: Cleveland)
- **Issue:** I had to call in because I couldn't use the audio, nothing was explained in the context that the general public could understand, spoke too fast couldn't really document how I wanted couldn't and lastly the agenda should be readily available on the documenters site so that I don't have to go looking for it
- **What was hard:** I had to call in because I couldn't use the audio, nothing was explained in the context that the general public could understand, spoke too fast couldn't really document how I wanted couldn't and lastly the agenda should be readily available on the documenters site so that I don't have to go looking for it

**Entry 4737** (Program: Chicago)
- **Issue:** Perhaps there should be some clarification as to which parts of the meeting fall under the Open Meeting Act and which do not- there was an executive meeting where the public was asked to leave.
- **What was hard:** Perhaps there should be some clarification as to which parts of the meeting fall under the Open Meeting Act and which do not- there was an executive meeting where the public was asked to leave.

**Entry 398** (Program: Detroit)
- **Issue:** What a lovely group. I'd be interested in covering the public hearing about the CPA building that they talked about today. That will be some time in May 2025. They seem to really work together well and enjoy one another. Really great Documenting assignment. :)
- **What was hard:** What a lovely group. I'd be interested in covering the public hearing about the CPA building that they talked about today. That will be some time in May 2025. They seem to really work together well and enjoy one another. Really great Documenting assignment. :)

**Entry 2976** (Program: Chicago)
- **Issue:** The meeting took place on their Vimeo city council channel, as opposed to their committee meeting channel.
- **What was hard:** The meeting took place on their Vimeo city council channel, as opposed to their committee meeting channel.

**Entry 4902** (Program: Chicago)
- **Issue:** They talk very fast and it's really hard to keep up with,  especially when you are not familiar with the subject. but I imagine even if you are. They deal with a lot of procurement contracts which I only was able to report very sketchily. Please also note in my report they have new restrictions on public comment, forbidding comments on anything already "under investigation."
- **What was hard:** They talk very fast and it's really hard to keep up with,  especially when you are not familiar with the subject. but I imagine even if you are. They deal with a lot of procurement contracts which I only was able to report very sketchily. Please also note in my report they have new restrictions on public comment, forbidding comments on anything already "under investigation."


## Key Findings

### Cluster Characteristics


## Methodology

1. **Text Preprocessing:** Feedback text was cleaned and normalized
2. **Embedding Generation:** Used sentence-transformers to create semantic embeddings
3. **Dimensionality Reduction:** Applied UMAP to reduce embeddings to 2D for visualization
4. **Clustering:** Used HDBSCAN algorithm to identify natural clusters in the data
5. **Visualization:** Created interactive plots using Plotly for exploration

## Next Steps

1. **Deep Dive Analysis:** Examine the content of each cluster to identify specific themes
2. **Outlier Investigation:** Analyze the small cluster to understand what makes these entries unique
3. **Action Items:** Develop targeted improvements based on the major themes identified
4. **Continuous Monitoring:** Set up regular clustering analysis to track changes over time

---

*This report was automatically generated from the documentation feedback clustering analysis.*
