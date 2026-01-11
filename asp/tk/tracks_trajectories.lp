% There are four cardinal directions:
% 0 = North, 1 = West, 2 = South, 3 = East
% numeric directions
n_dir(0..3).
% alphabetic directions
dir(n;w;s;e).
% mapping between numeric and alphabetic directions
dirmap(0, n).
dirmap(1, w).
dirmap(2, s).
dirmap(3, e).
% Four increments for counterclockwise rotation: 0, 90, 180, 270 degrees
rotation(0..3).

% TRACK AND CONNECTION DEFINITION
% track(ID, T, V, Rot): track with id ID of Type T (and variant V), rotated Rot times by 90 degrees (counterclockwise)
% connection(ID, A, In, Out): track with identifier ID allows transitions for a train facing In to change direction to Out via action A

% IDs of straight tracks (type 1) for easy reference
straight(ID) :- track(ID, 1, _, _).

% Type 1 (variant 1): Straight track
track(32800, 1, 1, 0). connection(32800, move_forward, 0, 0).
                       connection(32800, move_forward, 2, 2).
track(1025,  1, 1, 1).

% Type 1 (variant 2): Bend
track(4608,  1, 2, 0). connection(4608, move_forward, 3, 2).
                      connection(4608, move_forward, 0, 1).
track(16386, 1, 2, 1).
track(72,    1, 2, 2).
track(2064,  1, 2, 3).

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
connection(33825, move_forward, D, D) :- n_dir(D).

% Type 4: Single-slip switch
track(38433, 4, 1, 0).
connection(38433, move_forward, D, D) :- n_dir(D).
connection(38433, move_right, 3, 2). connection(38433, 0, 1, move_left).

track(50211, 4, 1, 1).
track(33897, 4, 1, 2).
track(35889, 4, 1, 3).

% Type 5: Double-slip switch
track(38505, 5, 1, 0).
connection(38505, move_forward, D, D) :- n_dir(D).
connection(38505, move_left, 0, 1). connection(38505, move_right, 3, 2).
connection(38505, move_right, 1, 0). connection(38505, move_left, 2, 3).

track(52275, 5, 1, 1).

% Type 6: Symmetrical Switch
track(20994, 6, 1, 0). connection(20994, move_left, 0, 1). connection(20994, move_right, 0, 3).
                       connection(20994, move_forward, 1, 2). connection(20994, move_forward, 3, 2).
track(16458, 6, 1, 1).
track(2136, 6, 1, 2).
track(6672, 6, 1, 3).

% rotate(RotD, Dir, Rot): direction RotD is obtained by rotating direction Dir counterclockwise by Rot × 90 degrees
rotate(RotD, Dir, Rot) :-
    n_dir(RotD), n_dir(Dir), rotation(Rot),
    RotD = (Dir + Rot) \ 4.

% infer all connections based on rotation of the 0 degree track ID for each type and variant cluster
connection(ID, A, In, Out) :- 
                        track(ID0, T, V, 0),
                        connection(ID0, A, In0, Out0),
                        track(ID, T, V, Rot),
                        rotate(In, In0, Rot),
                        rotate(Out, Out0, Rot).

% introduce new connections referring to alphabetic cardinal directions `n, w, s, e`
connection(ID, A, InV, OutV) :-
    connection(ID, A, In, Out),
    dirmap(In, InV),
    dirmap(Out, OutV).

% move(D, Y, X): moving in direction D changes grid location by Y (row) and X (column)
move(s,  1,  0).
move(n, -1,  0).
move(w,  0, -1).
move(e,  0,  1).

% cell_conn((Y,X), A, In, Out): Cell (Y,X) connects directions In and Out via action A
% cell_conn((Y,X), A, In, Out) :- cell((Y,X), Track), connection(Track, A, In, Out).
% cell_conn((Y0,X0), A, In, (Y1,X1), Out, Dur):
% Coming into cell (Y0,X0) in direction `In` can transition to cell (Y1,X1) in direction `Out` via action A taking Dur timesteps
cell_conn((Y0,X0), A, In, (Y1,X1), Out, 1) :-
    cell((Y0,X0), Track),
    connection(Track, A, In, Out),
    move(Out, DY, DX),
    Y1 = Y0 + DY, X1 = X0 + DX.

cell_conn(C0, A, In, C2, Out, Dur0+Dur1) :-
    cell(C0, T0), straight(T0),
    cell(C1, T1), straight(T1),
    cell(C2, T2), straight(T2),
    cell_conn(C0, A, In, C1, Inter, Dur0),
    cell_conn(C1, A, Inter, C2, Out, Dur1),
    A = move_forward.

% find the maximum connection for each action when only moving on straight tracks
max_conn(C0, A, In, X) :- cell_conn(C0, A, In, C1, Out, X), X = #max{ D: cell_conn(C0, A, In, _, _, D) }.

% add max_conns ending at target stations
max_conn(C0, A, In, D) :- cell_conn(C0, A, In, C1, Out, D), end(_, C1, _).

% trains can only wait on straight tracks, and only if the next cell in the current direction is non-straight (i.e., a switch or crossing)
% introduce `wait` actions for straight cells where a non-straight track is in Out direction
cell_conn(C0, wait, In, C0, In, 1) :-
    cell(C0, Track0),
    straight(Track0),
    cell_conn(C0, move_forward, In, C1, Out, _),
    cell(C1, Track1),
    not straight(Track1).

%wait_cell(C) :- cell_conn(C, wait, In, Out).

%#show wait_cell/1.