% time(T): T is a valid timestep for a state
time(0..MaxT) :- global(MaxT).

% Basic definitions: ACTION, STATE and ARRIVED
% action(train(ID), A, T): train ID performs action A at timestep T
% state(ID, (Y,X), D, T):  train ID is located at cell (Y,X), facing in direction D at timestep T
% state(ID, C, D, T):      alternative representation where C is the cell (if we don't need to access X and Y separately)
% arrived(ID, T):          train ID has arrived at its destination at timestep T

% train "waits" before its departure time
internal_action(train(ID), wait, T) :- time(T), start(ID, _, Dep, _), T < Dep.
% train 'moves forward' onto starting cell at departure time
internal_action(train(ID), move_forward, T) :-
    start(ID, _, Dep, _),
    time(T),
    T = Dep.
state(ID, C, Dir, T) :- start(ID, C, Dep, Dir), T = Dep + 1.

% -------------STATE PROPAGATION-------------
% for each time step and a given state choose one out of all available options, if the train has not reached its destination
% 1 { action(train(ID), A, T) : cell_conn(C, A, D, _) } 1 :- 
%         state(ID, C, D, T), time(T), 
%         not end(ID, C, _).

% speed_action(train(ID), A, T, S): train ID performs action A at timestep T with speed S
% choose either one or none of the available options (none to cover timesteps that are occupied by multi-timestep actions)
0 { speed_action(train(ID), A, T, S) : cell_conn(C, A, D, _) } 1 :- 
        state(ID, C, D, T), time(T), speed(ID, S),
        not end(ID, C, _).

% internal_action(train(ID), A, T): train ID performs internal action A at timestep T
% in case of speed actions, we need to expand them into multiple internal actions if they are non-wait actions
% A happens last (logical action)
internal_action(train(ID), A, T_last) :-
    speed_action(train(ID), A, T0, S),
    A < wait,
    T_last = T0 + S - 1.

% waits happen first (inserted waits)
internal_action(train(ID), wait, T1) :-
    speed_action(train(ID), A, T0, S),
    A < wait,
    T1 = T0 .. T0 + S - 2.

internal_action(train(ID), wait, T) :-
    speed_action(train(ID), wait, T, _).


% no train can perform two actions at the same time
:- internal_action(train(ID), A1, T), internal_action(train(ID), A2, T), A1 < A2.
% a train must perform an action at each timestep until it arrives
:- train(ID), time(T), arrived(ID, ArrT), T < ArrT,
   not internal_action(train(ID), _, T).

% move(D, Y, X): moving in direction D changes grid location by Y (row) and X (column)
move(s,  1,  0).
move(n, -1,  0).
move(w,  0, -1).
move(e,  0,  1).

% --- rule 1: movement (non-wait actions) ---
% moving_between(ID, C0, C1, D, T0, T1): 
%           at time step T0, train starts moving from cell C0 to cell C1, at which point it will face direction D
%           movement is finished at time step T1
%           Train blocks both cells C0 and C1 during the entire move
% used for collision detection during multi-timestep moves
moving_between(ID, (Y0,X0), (Y1,X1), Out, T0, T1) :-
    % gather state and (non-wait) action at timestep T0
    state(ID, (Y0,X0), D, T0),
    speed_action(train(ID), A, T0, S),
    A < wait,
    T1 = T0 + S,
    cell_conn((Y1,X1), A, D, Out),
    Y1 = Y0 + DY,
    X1 = X0 + DX,
    move(Out, DY, DX).
% #show moving_between/6.

state(ID, C1, D, T) :-
    moving_between(ID, _, C1, D, _, T).

% train 'occupies' both C0 and C1 during the entire movement between two cells
occupies(ID, (C0;C1), T) :-
    moving_between(ID, C0, C1, _, T0, T1),
    T = T0 .. T1.
% #show occupies/3.

% calculate the next state based on current state and action
state(ID, (Y2,X2), Out, T+1) :-
    % gather state and (non-wait) action at timestep T
    state(ID, (Y1,X1), D, T),
    internal_action(train(ID), A, T),
    % use `<` instead of `!=` for performance reasons
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
    internal_action(train(ID), wait, T).

% train also occupies the cell when waiting
occupies(ID, C, T+1) :-
    state(ID, C, D, T),
    internal_action(train(ID), wait, T).

% -------------CONSTRAINTS-------------

% All trains must arrive at some point
:- train(ID), not arrived(ID, _).

% collision constraints: during waiting, a train occupies one cell; during movement between two cells, it occupies both cells
:- occupies(ID0, C, T),
   occupies(ID1, C, T),
   ID0 != ID1.

% % vertex conflict: no two trains can occupy a cell at the same time
% :- state(ID, C, _, T),
%    state(ID', C, _, T),
%    ID != ID'.

% % edge conflict: no two trains can swap positions between consecutive timesteps
% :- state(ID, (Y1,X1), _, T),
%    state(ID, (Y2,X2), _, T+1),
%    state(ID2, (Y2,X2), _, T),
%    state(ID2, (Y1,X1), _, T+1),
%    ID != ID2,
%    time(T+1).

% MINIMIZATION GOALS
% late(ID, Delta): If train ID is delayed Delta indicates difference between actual arrival and expected arrival
late(ID, Delta) :-
    arrived(ID, T),
    end(ID, (_, _), Arr),
    T > Arr,
    Delta = T - Arr.
#show late/2.

% early(ID, Delta): If train ID arrives early Delta indicates the difference between expected and actual arrival 
early(ID, Delta) :-
    arrived(ID, T),
    end(ID, (_, _), Arr),
    T < Arr,
    Delta = Arr - T.
#show early/2.

% :- arrived(ID, T), end(ID, (_, _), Arr), T != Arr.

% action_count(ID, Count) :-
%     train(ID),
%     Count = #count { T : internal_action(train(ID), _, T) }.
% #show action_count/2.

% minimize wait actions
% #minimize { 2,ID,T : internal_action(train(ID), wait, T) }.
% #minimize { 1,ID,T : action(train(ID), _, T)}.

% minimize arrival times

#minimize { T, ID : arrived(ID, T) }.

% minimize early, late and no arrivals
%#minimize { Delta, ID : late(ID, Delta) }.
%#minimize { Delta, ID : early(ID, Delta) }.

% copy all speed predicates into action predicates
action(train(ID), A, T) :-
    speed_action(train(ID), A, T, _).

% copy all actions up until starting time
action(train(ID), A, T):- internal_action(train(ID), A, T), start(ID, _, Dep, _), T <= Dep.

% For each waiting internal_action inside a speed block,
% insert the block’s non-wait action A at that timestep.
action(train(ID), A, T1) :-
    speed_action(train(ID), A, T0, S),
    A < wait,
    T1 = T0 .. T0 + S - 1.


%#show speed_action/4.
%#show state/4.
% #show action/3.
% #show internal_action/3.
#show arrived/2.