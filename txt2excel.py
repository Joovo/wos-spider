#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
xlwt：创建excel的库
sheet.write(行坐标，列坐标，字符串等)
读取txt文件的每一行，每行字符串用空格划分
最后一项为施引专利储存在第2列
其余为专利号放第一列
'''
import xlwt

if __name__ == '__main__':
    wbk = xlwt.Workbook() # 创建文件
    sheet = wbk.add_sheet('sheet1')
    sheet.write(0,0,'专利号')
    sheet.write(0,1,'施引专利')
    row = 1

    with open('./wos2.txt', 'r') as file:
        for i in file.readlines(): # 读取每一行
            lst = i.split() # 用空格划分
            s = ''
            for i in range(len(lst)-1): # 除最后一列
                s += str(lst[i])
            sheet.write(row, 0, s)
            sheet.write(row, 1, lst[-1])
            if s=='':
                sheet.write(row, 0, '!!!!!!!')
            if lst[-1]=='':
                sheet.write(row, 1, '!!!!!!!')
            row += 1 # 行坐标+1
        wbk.save('wos.xls')
