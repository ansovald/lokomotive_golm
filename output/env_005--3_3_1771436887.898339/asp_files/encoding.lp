% time(T): T is a valid timestep for a state
time(0..MaxT) :- global(MaxT).

% Basic definitions: ACTION, STATE and ARRIVED
% action(train(ID), A, T): train ID performs action A at timestep T
% state(ID, (X,Y), D, T):  train ID is located at cell (X,Y), facing in direction D at timestep T
% state(ID, C, D, T):      alternative representation where C is the cell (if we don't need to access X and Y separately)
% arrived(ID, T):          train ID has arrived at its destination at timestep T

% train 'moves forward' onto starting cell at departure time
action(train(ID), move_forward, T) :-
    start(ID, _, Dep, _),
    time(T),
    T = Dep.
state(ID, C, Dir, T) :- start(ID, C, Dep, Dir), T = Dep + 1.

% -------------STATE PROPAGATION-------------
% for each time step and a given state choose one out of all available options, if the train has not reached its destination
1 { action(train(ID), A, T) : cell_conn(C, A, D, _) } 1 :- state(ID, C, D, T), time(T), not end(ID, C, _).

% move(D, Y, X): moving in direction D changes grid location by Y (row) and X (column)
move(s,  1,  0).
move(n, -1,  0).
move(w,  0, -1).
move(e,  0,  1).

% --- rule 1: movement (non-wait actions) ---
% calculate the next state based on current state and action
state(ID, (Y2,X2), Out, T+1) :-
    % gather state and (non-wait) action at timestep T
    state(ID, (Y1,X1), D, T),
    action(train(ID), A, T),
    A < wait,
    % infer next direction and cell
    cell_conn((Y1,X1), A, D, Out),
    Y2 = Y1 + DY,
    X2 = X1 + DX,
    move(Out, DY, DX).
% if the train reaches its destination, mark it as arrived
arrived(ID, T) :- state(ID, C, D, T), end(ID, C, _).

% --- rule 2: waiting (stay in same cell, direction doesn't change) ---
state(ID, C, D, T+1) :-
    state(ID, C, D, T),
    action(train(ID), wait, T).

% -------------CONSTRAINTS-------------

% All trains must arrive at some point
:- train(ID), not arrived(ID, _).

% vertex conflict: no two trains can occupy a cell at the same time
:- state(ID, C, _, T),
   state(ID', C, _, T),
   ID != ID'.

% edge conflict: no two trains can swap positions between consecutive timesteps
:- state(ID, (Y1,X1), _, T),
   state(ID, (Y2,X2), _, T+1),
   state(ID2, (Y2,X2), _, T),
   state(ID2, (Y1,X1), _, T+1),
   ID != ID2,
   time(T+1).

% MINIMIZATION GOALS
% late(ID, Delta): If train ID is delayed Delta indicates difference between actual arrival and expected arrival
late(ID, Delta) :-
    arrived(ID, T),
    end(ID, (_, _), Arr),
    T > Arr,
    Delta = T - Arr.

% early(ID, Delta): If train ID arrives early Delta indicates the difference between expected and actual arrival 
early(ID, Delta) :-
    arrived(ID, T),
    end(ID, (_, _), Arr),
    T < Arr,
    Delta = Arr - T.

% #minimize { 1 : action(train(ID), wait, T) }.

%*
% minimize arrival times
#minimize { T, ID : arrive(ID, T) }.

% minimize early, late and no arrivals
%#minimize { Delta, ID : late(ID, Delta) }.
%#minimize { Delta, ID : early(ID, Delta) }.
*%

#show state/4.
#show action/3.
#show arrived/2.