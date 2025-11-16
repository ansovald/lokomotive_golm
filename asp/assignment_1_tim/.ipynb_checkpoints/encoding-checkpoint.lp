%====================================================================
% TIME DOMAIN
%====================================================================
% finite time horizon
time(0..T) :- global(T).

%====================================================================
% BASE STATE
%====================================================================
% state(ID, (X,Y), D, T): train ID is located at (X,Y), facing in direction D at timestep T
state(ID, (X,Y), D, T) :-
    train(ID),
    start(ID, (X,Y), T, D),
    time(T).

%====================================================================
% ACTION SELECTION
%====================================================================
% choose some action
1 { action(train(ID), move_left, T);
    action(train(ID), move_right, T);
    action(train(ID), move_forward, T);
    action(train(ID), wait, T)
  } 1 :-
    state(ID, (X,Y), D, T),
    time(T).

%====================================================================
% DIRECTION RELATIONS
%====================================================================
% predicates defining what is left/right of cardinal direction
left_of(n, w).
left_of(e, n).
left_of(s, e).
left_of(w, s).

right_of(Y, X) :- left_of(X, Y).

%====================================================================
% ACTION RESTRICTIONS
%====================================================================
% forbid leftward movement if there is only one outward direction 
:- action(train(ID), move_left, T),
   state(ID, (X,Y), D, T),
   cell((X,Y), Track),
   #count { O : connection(Track, D, O) } = 1,
   time(T).

%*
% forbid rightward movement if there is only one outward direction 
:- action(train(ID), move_right, T),
   state(ID, (X,Y), D, T),
   cell((X,Y), Track),
   #count { O : connection(Track, D, O) } = 1,
   time(T).

% forbid rightward movement if there is no rightward path
:- action(train(ID), move_right, T),
   state(ID, (X,Y), D, T),
   cell((X,Y), Track),
   right_of(D, R),
   not connection(Track, D, R),
   time(T).

% forbid leftward movement if there is no leftward path
:- action(train(ID), move_left, T),
   state(ID, (X,Y), D, T),
   cell((X,Y), Track),
   left_of(D, L),
   not connection(Track, D, L),
   time(T).

%====================================================================
% MOVEMENT DEFINITIONS
%====================================================================
% move(D, X, Y): moving in direction D changes grid location by X and Y on the x-axis and y-axis
move(s, 0, -1).
move(n, 0, 1).
move(w, -1, 0).
move(e, 1, 0).

%====================================================================
% STATE TRANSITIONS
%====================================================================

% state transition via waiting
state(ID, (X, Y), D, T+1) :-
    time(T), time(T+1),
    action(train(ID), wait, T),
    state(ID, (X,Y), D, T).

% state transition via moving forward (unique outgoing connection)
state(ID, (X2, Y2), O, T+1) :-
    time(T), time(T+1),
    action(train(ID), move_forward, T),
    state(ID, (X,Y), D, T),
    cell((X,Y), Track),
    #count { O1 : connection(Track, D, O1) } = 1,
    connection(Track, D, O),
    move(O, X', Y'),
    X2 = X + X', Y2 = Y + Y',
    cell((X2,Y2), _).

% state transition via moving forward (multiple possible connections)
state(ID, (X2, Y2), D, T+1) :-
    time(T), time(T+1),
    action(train(ID), move_forward, T),
    state(ID, (X,Y), D, T),
    cell((X,Y), Track),
    #count { O : connection(Track, D, O) } > 1,
    move(D, X', Y'),
    X2 = X + X', Y2 = Y + Y',
    cell((X2,Y2), _).

% state transition via moving left
state(ID, (X2, Y2), L, T+1) :-
    time(T), time(T+1),
    action(train(ID), move_left, T),
    state(ID, (X,Y), D, T),
    left_of(D, L),
    move(L, X', Y'),
    X2 = X + X', Y2 = Y + Y',
    cell((X2,Y2), _).

% state transition via moving right
state(ID, (X2, Y2), R, T+1) :-
    time(T), time(T+1),
    action(train(ID), move_right, T),
    state(ID, (X,Y), D, T),
    right_of(D, R),
    move(R, X', Y'),
    X2 = X + X', Y2 = Y + Y',
    cell((X2,Y2), _).

%====================================================================
% SAFETY CONSTRAINTS
%====================================================================

% define invalid state for crashing
:- state(ID, (X,Y), _, T),
   state(ID', (X,Y), _, T),
   ID != ID'.

% Do not exceed the global time limit
:- state(ID, _, _, T),
   global(Tmax),
   T > Tmax.

% Do not move into empty cells
:- state(ID, (X,Y), _, T),
   cell((X,Y), 0).

% enforce that the train ends up at the final destination at the right time
:- end(ID, (X,Y), Arr),
   not state(ID, (X,Y), _, Arr).
*%

#show action/3.