[numj]=xlsread('20250720_P3_160℃_2col.xlsx','IGBT');%读取igbt.xlsx数据
Ti=numj(:,2);Ic=numj(1,3);
B=Ti;A=B;
q=length(A);
%%三点循环计数法；部分参考SAE ASTM标准
%% 步骤一%%
%对载荷时间历程进行处理使它只包含峰平谷谷交替出现
m=q;
for i=2:1:m-1
    if A(i)==A(i-1)
        B(i)=NaN;
    end
end
if A(m)==A(m-1)
    B(m)=NaN;
end
B(isnan(B))=[];
A=B;q=length(A);m=q;
for i=2:1:m-1
    if A(i-1)<A(i)&&A(i)<A(i+1)
        B(i)=NaN;
    elseif A(i-1)>A(i)&&A(i)>A(i+1)
        B(i)=NaN;
    end
end
B(isnan(B))=[];
%% 步骤二%%
%对载荷时间历程再造，使从最大（小）值拆开，前后拼接，使从最值开始最值结束
laa,ba=1;max(B);
if ba==1
    mi=min(B);
else
    mi=B(ba-1);
end
n=length(B);
B1=B(ba:n);
B2=B(1:ba);
if B1(end)==B2(1)
    B1(end)=NaN;
end
B=[B1;B2];
%% 步骤三 %%
%再只留波峰波谷，防止拼接处出现不合理的数据
A=B;m=length(B);
for i=2:1:m-1
    if A(i-1)<A(i)&&A(i)<A(i+1)
        B(i)=NaN;
    elseif A(i-1)>A(i)&&A(i)>A(i+1)
        B(i)=NaN;
    end
end
B(isnan(B))=[];n=length(B);
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% B为改造后载荷时间历程 n为B中波峰波谷的个数
%% 步骤四 %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%雨流计数记因素 1幅值F 2均值J 开启无脑循环模式
F=[];J=[];D=B;
while length(B)>=1
    n=length(B);
    if n==1
        break
    elseif n==2&&B(1)==B(2)
        F=[F; B(1)-mi];
        J=[J; (B(1)+mi)/2];
        B=[];
        break;
    elseif n>1
        for j=1:n-2
            s1=abs(B(j+1)-B(j));
            s2=abs(B(j+1)-B(j+2));
            e3=(B(j)+B(j+1))/2;
            if s1<=s2
                F=[F; s1];
                J=[J; e3];
                (j)=[];
                B(j)=[];
                n=length(B);
                break;
            else
                continue;
            end
        end
    end
    continue
end