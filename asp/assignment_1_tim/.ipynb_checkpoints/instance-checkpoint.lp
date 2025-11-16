% railways
cell((0,0), 16386).  cell((0,1), 1025).  cell((0, 2), 20994).  cell((0, 3), 5633).  cell((0, 4), 0).
cell((1,0), 16458).  cell((1,1), 5633).  cell((1,2), 3089).    cell((1,3), 52275).  cell((1,4), 4608).
cell((2,0), 72).     cell((2,1), 3089).  cell((2,2), 1025).    cell((2,3), 3089).   cell((2,4), 2064).

% train config
train(1).
start(1,(0,0),0,s).
end(1,(2,4),15).

%time
global(15).