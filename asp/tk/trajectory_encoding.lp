% time(T): T is a valid timestep for a state
time(0..MaxT) :- global(MaxT).

% Basic definitions: action, speed_action, state, and arrived
% action(train(ID), A, T): 
%           train ID performs action A at timestep T (needed for toolkit compatibility)
% speed_action(train(ID), A, T0, T1): 
%           train ID performs action A starting at timestep T0 and ending at timestep T1-1
%           (T1 marks the timestep after the action ends and marks the beginning of the next action)
% state(ID, (Y,X), D, T):  
%           train ID is located at cell (Y,X), facing in direction D at timestep T
% state(ID, C, D, T):      
%           alternative representation where C is the cell (if we don't need to access X and Y separately)
% arrived(ID, T):          
%           train ID has arrived at its destination at timestep T

% ------PRELIMINARIES FOR SPEED HANDLING------
% action_duration(A, S, Dur): action A takes Dur timesteps at speed S
move_action(move_left;move_right;move_forward).
action_duration(wait, S, 1) :- speed(_, S).
action_duration(A, S, S) :- move_action(A), speed(_, S).

action(train(ID), wait, T) :- start(ID, C, Dep, _), T=0..Dep-1.

% train 'moves forward' onto starting position at departure time
speed_action(train(ID), move_forward, Dep, Dep+1) :-
    start(ID, _, Dep, _).
state(ID, C, Dir, Dep+1) :- start(ID, C, Dep, Dir).

% ---------------ACTION CHOICE---------------
% after each speed action, choose exactly one valid action to perform next, unless the train has reached its destination
1 { speed_action(train(ID), A, T0, T1) : 
        % cell_conn(C0, A, In, C1, Out, ConnDur),
        max_conn(C0, A, In, ConnDur),
        action_duration(A, S, ActionDur),
        % T1 can exceed MaxT by 1, since it marks the timestep after the action ends
        T1 = T0 + ConnDur * ActionDur, global(MaxT), T1 <= MaxT + 1 } 1 :-
            speed_action(train(ID), _, _, T0),
            state(ID, C0, In, T0),
            speed(ID, S),
            not end(ID, C0, _).

% copy speed actions into regular actions (needed by toolkit)
% toolkit needs move_action at each timestep during the action
action(train(ID), A, T) :-
    speed_action(train(ID), A, T0, T1),
    T = T0..T1-1.

% -------------STATE PROPAGATION-------------
% calculate the next state based on current state and action
state(ID, C1, Out, T+S) :-
    % gather state and (non-wait) action at timestep T0. We reach the next state at T1 (after action ends)
    state(ID, C0, In, T),
    action(train(ID), A, T),
    A < wait,
    speed(ID, S),
    cell_conn(C0, A, In, C1, Out, 1).

state(ID, C, Dir, T+1) :-
    state(ID, C, Dir, T),
    action(train(ID), wait, T).

% if the train reaches its destination, mark it as arrived
arrived(ID, T) :- state(ID, C, D, T), end(ID, C, _).

% ---------COLLISION AVOIDANCE---------
% occupied(C, ID, T): cell C is occupied by train ID at timestep T
% during movement, a train occupies both the starting and ending cell for the whole duration of the move
occupied(C0, ID, T) :-
    state(ID, C0, _, T0),
    state(ID, C1, _, T1),
    speed(ID, S),
    T0 + S = T1,
    T = T0 .. T1.

occupied(C1, ID, T) :-
    state(ID, C0, _, T0),
    state(ID, C1, _, T1),
    speed(ID, S),
    T0 + S = T1,
    T = T0 .. T1.

% -------------CONSTRAINTS-------------
% no two trains can occupy the same cell at the same time
:- occupied(C, ID0, T),
   occupied(C, ID1, T),
   ID0 < ID1.

% all trains must arrive at some point
:- train(ID), not arrived(ID, _).

% trains must arrived at their designated arrival time
% :- arrived(ID, T), end(ID, (_, _), Arr), T != Arr.

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

% action_count(ID, Count) :-
%     train(ID),
%     Count = #count { T : speed_action(train(ID), _, T, _) }.
% #show action_count/2.

% minimize wait actions
% #minimize { 2,ID,T : speed_action(train(ID), wait, T, _) }.
% #minimize { 1,ID,T : action(train(ID), _, T)}.

% minimize arrival times

#minimize { T, ID : arrived(ID, T) }.

% minimize early and late arrivals
%#minimize { Delta, ID : late(ID, Delta) }.
%#minimize { Delta, ID : early(ID, Delta) }.

% #show speed_action/4.
% #show state/4.
% #show action/3.
#show arrived/2.