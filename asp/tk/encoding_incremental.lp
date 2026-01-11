#program base.
% ------PRELIMINARIES FOR SPEED HANDLING------
% action_duration(A, S, Dur): action A takes Dur timesteps at speed S
move_action(move_left;move_right;move_forward).
action_duration(wait, S, 1) :- speed(_, S).
action_duration(A, S, S) :- move_action(A), speed(_, S).

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

% toolkit ALWAYS requires a `wait` action at timestep 0 for each train, even if the departure time is 0
action(train(ID), wait, 0) :- train(ID).

% train "waits" before its departure time (even )
action(train(ID), wait, T) :- start(ID, _, Dep, _), T=0..Dep-1, Dep > 0.
% train "moves forward" onto starting cell at departure time. This takes 1 timestep regardless of speed.
% we need a speed_action here to for choosing the following speed_action at Dep+1
speed_action(train(ID), move_forward, Dep, Dep+1) :-
    start(ID, _, Dep, _), Dep > 0.
speed_action(train(ID), move_forward, 1, 2) :-
    start(ID, _, 0, _).
% state(ID, C, Dir, T): train ID is at cell C facing Dir at timestep T
% due to incremental solving, we need to explicitly define the actual action at Dep
action(train(ID), move_forward, Dep) :- start(ID, _, Dep, _), Dep > 0.

state(ID, C, Dir, T) :- speed_action(train(ID), move_forward, _, T), start(ID, C, _, Dir).
% occupied(C, ID, T) :-
%     state(ID, C, _, T).

#program check(t).
% check if all trains have arrived by time t
:- train(ID), not arrived(ID, _), query(t).
% :- train(ID), not arrived(ID).
% arrived(ID) :- arrived(ID, t), query(t).
%:- train(ID), not arrived(ID).
#external query(t).

#program step(t).
% ---------------ACTION CHOICE---------------
% after each speed action, choose exactly one valid action to perform next, unless the train has reached its destination
1 { speed_action(train(ID), A, t, T1) : 
        cell_conn(C, A, Dir, _), 
        action_duration(A, S, Dur),
        % T1 can exceed MaxT by 1, since it marks the timestep after the action ends
        T1 = t + Dur, global(MaxT), T1 <= MaxT + 1 } 1 :-
            speed_action(train(ID), _, _, t),
            state(ID, C, Dir, t),
            speed(ID, S),
            not end(ID, C, _).

% copy speed actions into regular actions (needed by toolkit)
action(train(ID), wait, t) :-
    speed_action(train(ID), wait, t, _).
% toolkit needs move_action at each timestep during the action
action(train(ID), A, t) :-
    speed_action(train(ID), A, T0, T1), move_action(A),
    T = T0..T1-1,
    T0 <= t, t <= T1-1.

% calculate the next state based on current state and action
state(ID, (Y1,X1), Out, T1) :-
    % gather state and (non-wait) action at timestep T0. We reach the next state at T1 (after action ends)
    state(ID, (Y0,X0), D, T0),
    speed_action(train(ID), A, T0, T1),
    T1 = t,
    A < wait,
    % infer next direction and cell
    cell_conn((Y0,X0), A, D, Out),
    Y1 = Y0 + DY,
    X1 = X0 + DX,
    move(Out, DY, DX).

state(ID, C, D, t) :-
    state(ID, C, D, t-1),
    action(train(ID), wait, t-1).

% if the train reaches its destination, mark it as arrived
arrived(ID, t) :- state(ID, C, D, t), end(ID, C, _).

% ---------COLLISION AVOIDANCE---------
% occupied(C, ID, T): cell C is occupied by train ID at timestep T
% during movement, a train occupies both the starting and ending cell for the whole duration of the move
occupied(C, ID, t) :-
    state(ID, C, _, T0),
    speed_action(train(ID), A, T0, T1),
    T0 <= t, t <= T1.

occupied(C, ID, t) :-
    state(ID, C, _, T1),
    speed_action(train(ID), A, T0, T1),
    T0 <= t, t <= T1.

% -------------CONSTRAINTS-------------
% no two trains can occupy the same cell at the same time
:- occupied(C, ID0, T),
   occupied(C, ID1, T),
   ID0 < ID1.

% all trains must arrive at some point
%:- train(ID), not arrived(ID, _).

% trains must arrived at their designated arrival time
% :- arrived(ID, T), end(ID, (_, _), Arr), T != Arr.

% MINIMIZATION GOALS
% late(ID, Delta): If train ID is delayed Delta indicates difference between actual arrival and expected arrival
late(ID, Delta) :-
    arrived(ID, t),
    end(ID, (_, _), Arr),
    t > Arr,
    Delta = t - Arr.
#show late/2.

% early(ID, Delta): If train ID arrives early Delta indicates the difference between expected and actual arrival 
early(ID, Delta) :-
    arrived(ID, t),
    end(ID, (_, _), Arr),
    t < Arr,
    Delta = Arr - t.
#show early/2.

% action_count(ID, Count) :-
%     train(ID),
%     Count = #count { T : speed_action(train(ID), _, T, _) }.
% #show action_count/2.

% minimize wait actions
% #minimize { 2,ID,T : speed_action(train(ID), wait, T, _) }.
% #minimize { 1,ID,T : action(train(ID), _, T)}.

% minimize arrival times

%#minimize { T, ID : arrived(ID, T) }.

% minimize early and late arrivals
%#minimize { Delta, ID : late(ID, Delta) }.
%#minimize { Delta, ID : early(ID, Delta) }.

% #show speed_action/4.
% #show state/4.
% #show action/3.
#show arrived/2.