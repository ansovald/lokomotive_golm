% Initialize directions and actions
direction(north; east; south; west).
action(move_forward; move_left; move_right; wait).

% Default action space: wait is always possible, position remains the same
action_space(C, wait, Dir) :- cell(C, Type), direction(Dir), Type != 0.
train_at(Train, C, T+1, Dir) :- action(train(Train), wait, T), train_at(Train, C, T, Dir), time(T).

%%%%%%%%%%%%%%%
% Track types %
%%%%%%%%%%%%%%%

% 32800: Straight North-South
action_space(C, move_forward, Dir) :- cell(C, 32800), Dir = (north; south).
train_at(Train, (X, Y-1), T+1, north) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, north), cell((X,Y), 32800), time(T).
train_at(Train, (X, Y+1), T+1, south) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, south), cell((X,Y), 32800), time(T).

% 1025: Straight East-West
action_space(C, move_forward, Dir) :- cell(C, 1025), Dir = (east; west).
train_at(Train, (X+1, Y), T+1, east) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, east), cell((X,Y), 1025), time(T).
train_at(Train, (X-1, Y), T+1, west) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, west), cell((X,Y), 1025), time(T).

% 16386: Top-left corner
action_space(C, move_forward, Dir) :- cell(C, 16386), Dir = (north; west).
train_at(Train, (X+1, Y), T+1, east) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, north), cell((X,Y), 16386), time(T).
train_at(Train, (X, Y+1), T+1, south) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, west), cell((X,Y), 16386), time(T).

% 72: Bottom-left corner
action_space(C, move_forward, Dir) :- cell(C, 72), Dir = (south; west).
train_at(Train, (X, Y-1), T+1, north) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, west), cell((X,Y), 72), time(T).
train_at(Train, (X+1, Y), T+1, east) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, south), cell((X,Y), 72), time(T).

% 4608: Top-right corner (east->south); (north->west)
action_space(C, move_forward, Dir) :- cell(C, 4608), Dir = (north; west).
train_at(Train, (X-1, Y), T+1, west) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, north), cell((X,Y), 4608), time(T).
train_at(Train, (X, Y+1), T+1, south) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, east), cell((X,Y), 4608), time(T).

% 2064: Bottom-right corner (south->west); (east->north)
action_space(C, move_forward, Dir) :- cell(C, 2064), Dir = (south; east).
train_at(Train, (X, Y-1), T+1, north) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, east), cell((X,Y), 2064), time(T).
train_at(Train, (X-1, Y), T+1, west) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, south), cell((X,Y), 2064), time(T).

% 5633: switch (east -> east;south); (north;west -> west)
action_space(C, move_right, east) :- cell(C, 5633).
action_space(C, move_forward, Dir) :- cell(C, 5633), Dir = (north; west; east).
train_at(Train, (X+1, Y), T+1, east) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, east), cell((X,Y), 5633), time(T).
train_at(Train, (X, Y+1), T+1, south) :- action(train(Train), move_right, T), train_at(Train, (X,Y), T, east), cell((X,Y), 5633), time(T).
train_at(Train, (X-1, Y), T+1, west) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, Dir), Dir=(north;west), cell((X,Y), 5633), time(T).

% 32872: switch (south -> south;east); (north;west -> north)
action_space(C, move_left, south) :- cell(C, 32872).
action_space(C, move_forward, Dir) :- cell(C, 32872), Dir = (north; south; west).
train_at(Train, (X, Y+1), T+1, south) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, south), cell((X,Y), 32872), time(T).
train_at(Train, (X+1, Y), T+1, east) :- action(train(Train), move_left, T), train_at(Train, (X,Y), T, south), cell((X,Y), 32872), time(T).
train_at(Train, (X, Y-1), T+1, north) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, Dir), Dir=(north;west), cell((X,Y), 32872), time(T).

% 37408: switch (south;east -> south); (north -> north; west)
action_space(C, move_left, north) :- cell(C, 37408).
action_space(C, move_forward, Dir) :- cell(C, 37408), Dir = (north; south; east).
train_at(Train, (X, Y-1), T+1, north) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, north), cell((X,Y), 37408), time(T).
train_at(Train, (X-1, Y), T+1, west) :- action(train(Train), move_left, T), train_at(Train, (X,Y), T, north), cell((X,Y), 37408), time(T).
train_at(Train, (X, Y+1), T+1, south) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, Dir), Dir=(south;east), cell((X,Y), 37408), time(T).

% 1097: switch (west -> west;north); (south;east -> east)
action_space(C, move_right, west) :- cell(C, 1097).
action_space(C, move_forward, Dir) :- cell(C, 1097), Dir = (west; south; east).
train_at(Train, (X-1, Y), T+1, west) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, west), cell((X,Y), 1097), time(T).
train_at(Train, (X, Y-1), T+1, north) :- action(train(Train), move_right, T), train_at(Train, (X,Y), T, west), cell((X,Y), 1097), time(T).
train_at(Train, (X+1, Y), T+1, east) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, Dir), Dir=(south;east), cell((X,Y), 1097), time(T).

% 2136: switch (south -> east;west); (west;east -> north)
action_space(C, (move_right;move_left), south) :- cell(C, 2136).
action_space(C, move_forward, Dir) :- cell(C, 2136), Dir = (east; west).
train_at(Train, (X-1, Y), T+1, west) :- action(train(Train), move_right, T), train_at(Train, (X,Y), T, south), cell((X,Y), 2136), time(T).
train_at(Train, (X+1, Y), T+1, east) :- action(train(Train), move_left, T), train_at(Train, (X,Y), T, south), cell((X,Y), 2136), time(T).
train_at(Train, (X, Y-1), T+1, north) :- action(train(Train), move_forward, T), train_at(Train, (X,Y), T, Dir), Dir=(east;west), cell((X,Y), 2136), time(T).