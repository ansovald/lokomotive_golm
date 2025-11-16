 % There are four cardinal directions:
% 0 = North, 1 = West, 2 = South, 3 = East
dir(0..3).
inc(0..3).

% predicate documentation
% track(ID, T, V, Inc): track with id ID of Type T (and variant V) has been rotated Inc times by 90 degrees
% connection(ID, A, In, Out): track with identifier ID connects allows transitions for a train facing In to change direction to Out via action A

% Type 1 (variant 1): Straight track
track(32800, 1, 1, 0). connection(32800, move_forward, 0, 0).
                       connection(32800, move_forward, 2, 2).
track(1025, 1, 1, 1).

% Type 1 (variant 2): Straight track
track(4608, 1, 2, 0). connection(4608, move_forward, 3, 2).
                      connection(4608, move_forward, 0, 1).
track(16386, 1, 2, 1).
track(72, 1, 2, 2).
track(2064, 1, 2, 3).

% Type 2 (variant 1): Simple switch 
track(37408, 2, 1, 0). connection(37408, move_left, 0, 1). connection(37408, move_forward, 2, 2). connection(37408, move_forward, 0, 0).
                       connection(37408, move_forward, 3, 2). connection(37408, move_forward, 0, 0).
track(17411, 2, 1, 1).
track(32872, 2, 1, 2).
track(3089, 2, 1, 3).

% Type 2 (variant 2): Simple switch
track(49186, 2, 2, 0). connection(49186, move_right, 0, 3). connection(49186, move_forward, 2, 2).
                       connection(49186, move_forward, 1, 2). connection(49186, move_forward, 0, 0).
track(1097, 2, 2, 1).
track(34864, 2, 2, 2).
track(5633, 2, 2, 3).


% Type 3: Diamond crossing
track(33825, 3, 1, 0).
connection(33825, move_forward, D, D) :- dir(D).

% Type 4: Single-slip switch
track(38433, 4, 1, 0).
connection(38433, move_forward, D, D) :- dir(D).
connection(38433, move_right, 3, 2). connection(38433, 0, 1, move_left).

track(50211, 4, 1, 1).
track(33897, 4, 1, 2).
track(35889, 4, 1, 3).

% Type 5: Double-slip switch
track(38505, 5, 1, 0).
connection(38505, move_forward, D, D) :- dir(D).
connection(38505, move_left, 0, 1). connection(38505, move_right, 3, 2).
connection(38505, move_right, 1, 0). connection(38505, move_left, 2, 3).

track(52275, 5, 1, 1).

% Type 6: Symmetrical Switch
track(20994, 6, 1, 0). connection(20994, move_left, 0, 1). connection(20994, move_right, 0, 3).
                       connection(20994, move_forward, 1, 2). connection(20994, move_forward, 3, 2).
track(16458, 6, 1, 1).
track(2136, 6, 1, 2).
track(6672, 6, 1, 3).

% rotate(X, Y, Inc): direction X is obtained by rotating direction Y counterclockwise by Inc × 90 degrees
rotate(X, Y, Inc) :-
    dir(X), dir(Y), inc(Inc),
    X = (Y + Inc) \ 4.

% infer all connections based on rotation of the 0 degree track ID for each type and variant cluster
connection(ID, A, X, Y) :- track(ID0, T, V, 0),
                        track(ID, T, V, Inc),
                        connection(ID0, A, D1, D2),
                        rotate(X, D1, Inc),
                        rotate(Y, D2, Inc).

% you can always wait
connection(ID, wait, X, X) :- connection(ID, _, X, Y).

% introduce new connections reffering to cardinal directions explicitly
dirmap(0, n).
dirmap(1, w).
dirmap(2, s).
dirmap(3, e).
connection(ID, A, Xs, Ys) :-
    connection(ID, A, X, Y),
    dirmap(X, Xs),
    dirmap(Y, Ys).

% cell_conn((X,Y), A, In, Out): Cell (X,Y) connects directions In and Out via action A
cell_conn((X,Y), A, In, Out) :- cell((X,Y), Track), connection(Track, A, In, Out), dirmap(_,In), dirmap(_,Out).