% time(T): T is a valid timestep for a state
time(0..MaxT) :- global(MaxT).

% emit waiting actions until departure
action(train(ID), wait, T) :-
    start(ID, (_, _), Dep, _),
    time(T),
    T < Dep.

% -------------STATE PROPAGATION-------------
% state(ID, (X,Y), D, T): train ID is located at (X,Y), facing in direction D at timestep T
state(ID, (X,Y), Dir, Dep) :- start(ID, (X,Y), Dep, Dir).

% for each time step and a given state choose one out of all available options
1{ action(train(ID), A, T) : cell_conn((X,Y), A, D, _) }1 :- state(ID, (X,Y), D, T), time(T).

% move(D, X, Y): moving in direction D changes grid location by X and Y on for row and column wise respectively 
move(s, 1, 0).
move(n, -1, 0).
move(w, 0, -1).
move(e, 0, 1).

can_move(ID, T) :-
    time(T),
    start(ID,(_, _), Dep, _),
    #count { T1 : action(train(ID), A1, T1), A1 != wait, T1 >= Dep, T1 < T } >= 1.

%destination: train ID has cell (X,Y) as its destination
destination(ID, (X, Y)) :- end(ID, (X,Y), _).

% First non-wait after Dep: keep the train in place (no movement yet)
state(ID, (X,Y), D, Tnext) :-
    state(ID, (X,Y), D, T),
    action(train(ID), A, T),
    A != wait,
    not can_move(ID, T), 
    Tnext = T + 1,
    time(T),
    time(Tnext),
    not destination(ID, (X,Y)).

% --- rule 1: movement (non-wait actions) ---
state(ID, (X2,Y2), Out, Tnext) :-
    % gather state and (non-wait) action at timestep T
    state(ID, (X1,Y1), D, T),
    action(train(ID), A, T),
    A != wait,
    % infer next direction and cell
    cell_conn((X1,Y1), A, D, Out),
    X2 = X1 + DX,
    Y2 = Y1 + DY,
    Tnext = T + 1,
    time(T),
    time(Tnext),
    move(Out, DX, DY),
    % only propagate states if train has started rolling at some point
    can_move(ID, T),
    % only propagate states if train has not arrived yet
    not destination(ID, (X1,Y1)).

% --- rule 2: waiting (stay in same cell) ---
state(ID, (X,Y), Out, Tnext) :-
    state(ID, (X,Y), D, T),
    action(train(ID), wait, T),
    cell_conn((X,Y), wait, D, Out),
    Tnext = T + 1,
    time(T),
    time(Tnext),
    not destination(ID, (X,Y)).

% -------------CONSTRAINTS-------------
% vertex conflict: no two trains can occupy a cell at the same time
:- state(ID, (X,Y), _, T),
   state(ID', (X,Y), _, T),
   ID != ID'.

% edge conflict: no two trains can swap positions between consecutive timesteps
:- state(ID, (X1,Y1), _, T),
   state(ID, (X2,Y2), _, T+1),
   state(ID2, (X2,Y2), _, T),
   state(ID2, (X1,Y1), _, T+1),
   ID != ID2,
   time(T+1).

% Do not move into empty cells (redundant)
:- state(ID, (X,Y), _, T),
   cell((X,Y), 0).


% enforce that trains end occupies final destination at the arrival time (deprecated constraint)
:- end(ID, (X,Y), Arr),
   not state(ID, (X,Y), _, Arr).



% minimization block
% arrive(ID,T): Train ID arrived at its destination at timestep T
arrive(ID,T) :-
    state(ID, (X,Y), _, T),
    end(ID, (X,Y), _).

% late(ID, Delta): If train ID is delayed Delta indicates difference between actual arrival and expected arrival
late(ID, Delta) :-
    arrive(ID, T),
    end(ID, (_, _), Arr),
    T > Arr,
    Delta = T - Arr.

% early(ID, Delta): If train ID arrives early Delta indicates the difference between expected and actual arrival 
early(ID, Delta) :-
    arrive(ID, T),
    end(ID, (_, _), Arr),
    T < Arr,
    Delta = Arr - T.


% train never arrives at its destination
% :- end(ID, (_, _), _), not arrive(ID, _).



#minimize { 1 : action(train(ID), wait, T) }.

%*
% minimize arrival times
%#minimize { T, ID : arrive(ID, T) }.

% minimize early, late and no arrivals
%#minimize { Delta, ID : late(ID, Delta) }.
%#minimize { Delta, ID : early(ID, Delta) }.
*%

%#show state/4.
#show action/3.