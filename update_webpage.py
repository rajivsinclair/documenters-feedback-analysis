#!/usr/bin/env python3
"""
Create updated webpage with proper cluster descriptions based on real examples
"""

cluster_descriptions = {
    0: {
        'title': 'Process & Learning Feedback',
        'icon': 'bi-mortarboard',
        'percentage': '14.7%',
        'count': 724,
        'description': '''
        This cluster captures documenters sharing their learning process, first-time experiences, 
        and feedback about the documentation toolkit and process itself. These entries focus on 
        self-reflection, procedural suggestions, and personal experiences navigating assignments.
        ''',
        'key_insight': '''
        New documenters need better onboarding resources and experienced documenters are 
        actively sharing knowledge about best practices and procedural improvements.
        ''',
        'examples': [
            "I recommend links to the facilities (Dickerson, JDF, etc.); a legal glossary; and a review of the last proceedings to help new Documenters...",
            "Had a great time doing this assignment. Toolkit contents were useful, and directions were easy to understand...",
            "Thank you for the opportunity as this is my first paid Documenters assignment. I welcome any and all feedback...",
            "I think a script that would help people understand the direction of the project would help us help you...",
            "It would be great if there were a way to upload multiple files at a time (takes awhile to upload all the screenshots)..."
        ]
    },
    1: {
        'title': 'Meeting Access & Organization Issues',
        'icon': 'bi-door-open',
        'percentage': '30.8%',
        'count': 1519,
        'description': '''
        This cluster focuses on barriers to accessing and following meetings, including missing agendas, 
        poor audio quality, inability to identify speakers, and general organizational problems that 
        prevent effective documentation and public participation.
        ''',
        'key_insight': '''
        Meeting organizers need standardized protocols for agenda distribution, speaker identification, 
        and audio quality to ensure both documenters and the public can effectively follow proceedings.
        ''',
        'examples': [
            "Very few copies of physical agendas were provided at the meeting, but having a place to find this online beforehand would be beneficial...",
            "The audio for this meeting was terrible. The only person I could hear adequately most of the time was the Chair...",
            "I couldn't find a list of members of this board anywhere. One of the speakers was listed as 'landmarks' - are these always the same people?...",
            "There was no meeting agenda made available to the public. Was unable to identify speakers in the meeting apart from the presenters...",
            "Try to figure out how to hear and see all of the Commissioners. Due to the way they are set up it is difficult to see individuals names..."
        ]
    },
    2: {
        'title': 'Community Engagement & Civic Process',
        'icon': 'bi-people',
        'percentage': '29.6%',
        'count': 1456,
        'description': '''
        This cluster emphasizes community participation, public discourse, and the civic engagement 
        aspects of meetings. Documenters describe community attendance, public comment effectiveness, 
        and how well meetings serve their democratic function of public participation.
        ''',
        'key_insight': '''
        Documenters observe significant community engagement challenges and opportunities, noting 
        when public participation is effective versus when procedural barriers limit civic engagement.
        ''',
        'examples': [
            "This was a great event. I would say about 75-85 people were in attendance and were attentive to what the candidates had to say...",
            "This assignment was truly eye opening on Public Discourse of Community Engagement in Planning, TIFs, Developments in Chicago...",
            "Although commissioners and some in public attendance had very strong disagreements, things remained civil and all agenda items were addressed...",
            "They seemed to be able to address most public comment concerns either immediately or advising of a follow up...",
            "Before the meeting, I found it helpful to look on the Board's Web page at 'Cases Currently Before the Police Board'..."
        ]
    },
    3: {
        'title': 'Technical Infrastructure & Virtual Meetings',
        'icon': 'bi-camera-video',
        'percentage': '24.9%',
        'count': 1227,
        'description': '''
        This cluster addresses technical challenges with virtual and hybrid meetings, including 
        streaming issues, audio/video problems, recording difficulties, and the logistics of 
        documenting meetings that blend in-person and virtual participation.
        ''',
        'key_insight': '''
        Virtual and hybrid meeting infrastructure requires significant improvement, with consistent 
        audio/video quality and reliable streaming being essential for effective documentation.
        ''',
        'examples': [
            "This was a hybrid meeting so some members were in person and others on Microsoft Teams. Not everyone was clearly identifiable or audible...",
            "I had trouble with Vimeo livestream page - could not consistently get both audio and video, and I'm tech savvy enough...",
            "my sound went out about 1:34 started back up with sound at 1:49 and that was the end of the meeting...",
            "Unlike regular board meetings, this one only featured the shared screen--no view of the room or participants. Kind of weird...",
            "The audio quality coming through was pretty bad, so I'm not entirely sure what to do in that type of situation..."
        ]
    }
}

# Create HTML content
html_clusters = ""
for cluster_id, info in cluster_descriptions.items():
    examples_html = ""
    for i, example in enumerate(info['examples'], 1):
        examples_html += f'''
        <div class="example-feedback">
            <strong>{i}.</strong> "{example}"
        </div>'''
    
    html_clusters += f'''
    <div class="cluster-card">
        <h4><i class="{info['icon']}"></i> Cluster {cluster_id}: {info['title']} ({info['count']:,} entries - {info['percentage']})</h4>
        <p>
            {info['description'].strip()}
        </p>
        <div class="key-insight">
            <strong>Key Insight:</strong> {info['key_insight'].strip()}
        </div>
        <div class="examples-section">
            <strong>Representative Examples:</strong>
            {examples_html}
        </div>
    </div>
    '''

print("=== HTML CLUSTER DESCRIPTIONS ===")
print(html_clusters)