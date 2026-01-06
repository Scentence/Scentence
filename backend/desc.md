"""
1) 사용자가 입력한 질문(쿼리)을 보고 사용자 입력이 애매하거나 추가적인 정보가 필요하면 interviewer로 보냄
2) 사용자 질문이 검색할 필요가 없을때 바로 writer로 보냄
3) 사용자 질문이 추천을 수행할정도로 충분할 때 researcher로 보냄

[예상되는 흐름]
a)
Supervision → Interviewer
a-1)
Interviewer → User
a-2)
Interviewer → Researcher
Researcher → Writer
b)
Supervision → Researcher
Researcher → Writer
Writer → User
c)
Supervision → Writer
Writer → User
"""

***********************************************************
graph TD
    START([START]) --> supervisor[Supervisor<br/>라우팅 결정]
    
    supervisor -.->|interviewer| interviewer[Interviewer<br/>명확화 질문]
    supervisor -.->|researcher| researcher[Researcher<br/>조사 수행]
    supervisor -.->|writer| writer[Writer<br/>최종 응답]
    
    interviewer --> researcher
    researcher --> writer
    
    writer --> END([END])
***********************************************************


graph TD
    START([START]) --> supervisor[supervisor]
    
    supervisor -->|interviewer| interviewer[interviewer]
    supervisor -->|researcher| researcher[researcher]
    supervisor -->|writer| writer[writer]
    
    interviewer -->|user_input| user_input[user_input]
    interviewer -->|researcher| researcher
    
    user_input -->|researcher| researcher
    
    researcher --> writer
    writer --> END([END])


graph TD;
        __start__([<p>__start__</p>]):::first
        supervisor(supervisor)
        interviewer(interviewer)
        researcher(researcher)
        writer(writer)
        __end__([<p>__end__</p>]):::last
        __start__ --> supervisor;
        interviewer --> researcher;
        researcher --> writer;
        supervisor -.-> interviewer;
        supervisor -.-> researcher;
        supervisor -.-> writer;
        writer --> __end__;
        classDef default fill:#f2f0ff,line-height:1.2
        classDef first fill-opacity:0
        classDef last fill:#bfb6fc