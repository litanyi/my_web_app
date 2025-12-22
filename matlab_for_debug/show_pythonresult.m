% 1. 设置Excel文件路径（替换为你的文件实际路径，比如'C:\文件夹\Temperature.xlsx'）
filename = '../rainflowcount.csv';  

% 2. 读取Excel表格（自动识别列名，如“幅值”“均值”）
dataTable = importdata(filename);  
dataTable= dataTable.data;

% 3. 提取“幅值”和“均值”两列数据
F_amplitude = dataTable(:,1);  % 第一列：幅值
J_meanValue = dataTable(:,2);   % 第二列：均值

F_diff = F_amplitude - F;

D_code = importdata('../Load1.txt');
final_points_code = importdata('../final_turning.txt');
optimized_points_code = importdata('../optimized_points.txt');
turning_points_code = importdata('../turning_points.txt');
raw_points_code = importdata('../raw_points.txt');

plot(F,J,'o',F_amplitude,J_meanValue,'*')
legend('CRRC','code')
xlabel('幅度')
ylabel('均值')
F_error = norm(F_amplitude-F,2)/norm(F,2)
J_error = norm(J_meanValue-J,2)/norm(J,2)