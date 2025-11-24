clear;clc

%% 三点法 %%

fprintf('三点法\n')

tic

%Load=xlsread('G:\桌面\随机数');%%在此修改加载的文件名，数据格式一直才可正确运算%%

Load=randi([-300,300],10000,1); %取样范围为(-300,300)，取样点 10000 个。

Load1=Load;Load2=Load;

L3=length(Load2);

%三点循环计数法；部分参考SAE ASTM标准

%% 步骤一 %%

%对载荷时间历程进行处理使它只包含峰谷峰谷交替出现

m1=L3;

for i=2:1:m1-1

    if Load2(i-1)<=Load2(i)&&Load2(i)<=Load2(i+1)

        Load1(i)=NaN;

    elseif Load2(i-1)>=Load2(i)&&Load2(i)>=Load2(i+1)

        Load1(i)=NaN;

    end

end

Load1(isnan(Load1))=[];

%% 步骤二 %%

%对载荷时间历程再造，使从最大（小）值拆开，前后拼接，使从最值开始最值结束

[a,b]=max(Load1);

n1=length(Load1);

B1=Load1(b:n1);

B2=Load1(1:b);

Load1=[B1;B2];

%% 步骤三 %%

%再只留波峰波谷，防止拼接处出现不合理的数据

Load2=Load1;m1=length(Load1);

for i=2:1:m1-1

    if Load2(i-1)<Load2(i)&&Load2(i)<Load2(i+1)

        Load1(i)=NaN;

    elseif Load2(i-1)>Load2(i)&&Load2(i)>Load2(i+1)

        Load1(i)=NaN;

    end

end

Load1(isnan(Load1))=[];n1=length(Load1);

% B为改造后载荷时间历程  n为B中波峰波谷的个数

%% 步骤四 %%

%雨流计数记因素  1幅值F 2均值J  开启无脑循环模式

Amplitude=[];Mean=[];

while length(Load1)>=1

    n1=length(Load1);

    if n1==1||n1==2

        break

    elseif n1>2

        for j=1:n1-2

            s1=abs(Load1(j+1)-Load1(j));

            s2=abs(Load1(j+1)-Load1(j+2));

            e3=(Load1(j+1)+Load1(j+2))/2;

            if s1<=s2

                Amplitude=[Amplitude;s1];

                Mean=[Mean;e3];

                Load1(j)=[];

                Load1(j)=[];

                n1=length(Load1);

                break;

            else

                continue;

            end

        end

    end

    continue

end

D1=Load1;

%% 步骤五 %%

%画图像 三维hist三维图像

X=[Mean,Amplitude];

subplot(2,2,1);

%figure(2);

hist3(X,[30 30]);

xlabel('均值');

title('雨流计数法-三点循环计数运算逻辑');

ylabel('幅值');

zlabel('循环次数');

subplot(2,2,2);

plot(D1,'r-*');

title('余项');

toc

%% 四点法 %%

fprintf('四点法\n')

tic

Load3=Load;Load4=Load;

L4=length(Load3);

%四点循环计数法

%% 步骤一 %%

%对载荷时间历程进行处理使它只包含峰谷峰谷交替出现

for i=2:1:L4-1

    if  Load4(i-1)==Load4(i)

        Load3(i-1)=NaN;

    else

        continue

    end

end

Load3(isnan(Load3))=[];

Load4=Load3;

L4=length(Load3);

for i=2:1:L4-1

    if Load4(i-1)<=Load4(i)&&Load4(i)<=Load4(i+1)

        Load3(i)=NaN;

    elseif Load4(i-1)>=Load4(i)&&Load4(i)>=Load4(i+1)

        Load3(i)=NaN;

    end

end

Load3(isnan(Load3))=[];n2=length(Load3);

%% 步骤二 %%

Amplitude=[];Mean=[];

while ex(Load3)==1||ex(Load3)==0

 if ex(Load3)==1

      for j=1:n2-3

        if (Load3(j)<=Load3(j+2)&&Load3(j)<=Load3(j+1)&& Load3(j+1)<=Load3(j+3))||(Load3(j)>=Load3(j+2)&&Load3(j)>=Load3(j+1)&& Load3(j+1)>=Load3(j+3))

            s1=abs(Load3(j+1)-Load3(j+2));

            e3=(Load3(j+2)+Load3(j+1))/2;

            Amplitude=[Amplitude;s1];

            Mean=[Mean;e3];

            Load3(j+1)=[];

            Load3(j+1)=[];

            n2=length(Load3);

            break

        else

            continue

        end

      end

 else

     if ex(Load3)==0

     break

     end

 end

 continue

end

D2=Load3;

%% 步骤三 %%

%画图像 三维hist三维图像

Y=[Mean,Amplitude];

subplot(2,2,3);

%figure(2);

hist3(Y,[30 30]);

xlabel('均值');

title('雨流计数法-四点循环计数运算逻辑');

ylabel('幅值');

zlabel('循环次数');

subplot(2,2,4);

plot(D2,'r-*');

title('残余项');

toc

function re=ex(B)

n=length(B);re=0;

for j=1:n-3

    if  (B(j)<=B(j+2)&&B(j)<=B(j+1)&& B(j+1)<=B(j+3))||(B(j)>=B(j+2)&&B(j)>=B(j+1)&& B(j+1)>=B(j+3))

        re=1;

        break

    else

        re=0;

        continue

    end

end

end
