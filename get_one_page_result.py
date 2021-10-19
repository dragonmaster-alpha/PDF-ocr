from PIL import ImageTk, Image
import cv2
import pytesseract 
import argparse
import os
import imutils
import cv2
from fuzzywuzzy import process
import mysql.connector

def main(filename):
    pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

    THRESH = 10
    REF_STR = 'Referenz'
    IHR_REF = 'Ihre Referenz'
    UNS_REF = 'Unsere Referenz'
    TABLE_HEADER = 'Pos Menge'
    TABLE_HEIGHT = 75

    addr_x_min_pos = 820
    addr_y_min_pos = 350
    x_max_pos = 1524
    addr_y_max_pos = 550
    item_y_max_pos = 1800
    table_y = 700

    result = {}
    item = []

    def IsInAddrRegion(x, y, w, h):
        # return (x >= addr_x_min_pos and y >= addr_y_min_pos and (y + h) <= addr_y_max_pos)
        return (x >= addr_x_min_pos and y >= 250 and (y + h) <= addr_y_max_pos)

    def DetectTextFromImg(img):
        return pytesseract.image_to_string(img)

    def GetAddrInfo(str):
        addr_list = str.splitlines()
        addr_list = list(filter(None, addr_list))
        #print(addr_list)
        result['company_name'] = addr_list[0]
        if (len(addr_list) == 3):
            result['reference_name'] = ''
            result['street'] = addr_list[1]
            result['city'] = addr_list[2]
        elif(len(addr_list) == 4):
            result['reference_name'] = addr_list[1]
            result['street'] = addr_list[2]
            result['city'] = addr_list[3]
        else:
            result['reference_name'] = addr_list[1]
            result['street'] = ''
            result['city'] = ''
        #print(result)

    def FindBestMatchString(str, str_list):
        Ratios = process.extractOne(str, str_list)
        expected_text = Ratios[0]
        return expected_text

    def GetReferenceName(expected_text):
        exp = expected_text.split()
        search_str = FindBestMatchString(REF_STR, exp)
        cnt = len(exp)
        for i in range(cnt - 1, -1, -1):
            if (exp[i] == search_str):
                break
        res = ''
        for j in range(i + 1, cnt):
            res = res + exp[j]
            if (j + 1 != cnt):
                res += ' '
        return res


    def GetReferences(filename):
        img = Image.open(filename)
        text = pytesseract.image_to_string(img)
        tot_text = text.splitlines()
        tot_text = list(filter(None, tot_text))

        if (len(tot_text)):

            expected_text = FindBestMatchString(IHR_REF, tot_text)
            
            result['ihr_ref'] = GetReferenceName(expected_text)

            expected_text = FindBestMatchString(UNS_REF, tot_text)
            result['uns_ref'] = GetReferenceName(expected_text)

        #print(result)

    def CheckFloat(str):
        try:
            float(str)
            return True
        except ValueError:
            return False    
    
    def GetItemArea(pos_array, original):
        pos_array = sorted(pos_array, key=lambda k: k['x'])
        array = []
        prev_y = pos_array[0]['y']
        #print(pos_array)
        for pos in pos_array:
            if (pos['x'] >= 310):
                ROI = original[pos['y'] - 20:pos['y'] + pos['h'] + 20, pos['x'] - 20:pos['x'] + pos['w'] + 20]
                if (pos['x'] >= 800):
                    ROI = original[pos['y'] - 10:pos['y'] + pos['h'] + 20, pos['x'] - 30:pos['x'] + pos['w'] + 30]
                txt = DetectTextFromImg(ROI)
                txt_list = txt.splitlines()
                txt_list = list(filter(None, txt_list))
                txt_list = list(filter(lambda txt: txt.strip(), txt_list))
                if (len(txt_list) == 0):
                    continue
                txt_list = ' '.join(txt_list)
                # print(txt_list)
                if (abs(prev_y - pos['y']) >= 20 and len(array) == 4):
                    mwst = ''.join(array[2].split())
                    if (mwst[len(mwst) - 1] == '%'):
                        if (CheckFloat(array[1])):
                            item.append({'item_no': array[0], 'item_desc': '', 'price': array[1], 'mwst': mwst, 'totprice': array[3]})
                        else:
                            item.append({'item_no': array[0], 'item_desc': array[1], 'price': '', 'mwst': mwst, 'totprice': array[3]})
                    array.clear()
                    prev_y = pos['y']
                
                array.append(txt_list)
                if (len(array) == 5):
                    item.append({'item_no': array[0], 'item_desc': array[1], 'price': array[2], 'mwst': ''.join(array[3].split()), 'totprice': array[4]})
                    array.clear()
        if (len(array) == 5):
            if (CheckFloat(array[2])):
                item.append({'item_no': array[0], 'item_desc': array[1], 'price': array[2], 'mwst': ''.join(array[3].split()), 'totprice': array[4]})
            array.clear()
        elif (len(array) == 4):
            if (CheckFloat(array[1])):
                item.append({'item_no': array[0], 'item_desc': '', 'price': array[1], 'mwst': ''.join(array[2].split()), 'totprice': array[3]})
            else:
                item.append({'item_no': array[0], 'item_desc': array[1], 'price': '', 'mwst': ''.join(array[2].split()), 'totprice': array[3]})
            array.clear()

    def FindingRectContours(filename, ind = 0):
        image = cv2.imread(filename)
        original = image.copy()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (51, 45), 0)   #This Gaussian Blur threshold seems the best match for our needs.
        thresh = cv2.threshold(blurred, 230,255,cv2.THRESH_BINARY_INV)[1]

        # Find contours
        cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]

        # Iterate thorugh contours and filter for ROI
        image_number = 0
        pos_array = []

        for c in cnts:
            #area = cv2.contourArea(c)

            x,y,w,h = cv2.boundingRect(c)
            cv2.rectangle(image, (x, y), (x + w, y + h), (36,255,12), 2)
            if (y > table_y):
                pos_array.append({'x': x, 'y': y, 'w': w, 'h': h})
            # ROI = original[y:y+h, x:x+w]
            if (IsInAddrRegion(x, y, w, h)):       
                ROI = original[y-THRESH:y+h+THRESH, x-THRESH:x+w+THRESH] 
                #cv2.imwrite("New/addr_{}.png".format(ind), ROI)
                addr = DetectTextFromImg(ROI)
                test = addr.splitlines()
                test = list(filter(None, test))
                # print(addr)
                #print(test)
                if (len(test) >= 2):
                    GetAddrInfo(addr)
            #cv2.imwrite("New/ROI_{}.png".format(image_number), ROI)
            image_number += 1

        pos_array = sorted(pos_array, key=lambda k: k['y'])
        cnt = len(pos_array)
        miny = 0
        i = 0
        for i in range(0, cnt):
            pos = pos_array[i]
            ROI = original[pos['y'] - THRESH:pos['y'] + pos['h'] + THRESH, pos['x'] - THRESH:pos['x'] + pos['w'] + THRESH]
            txt = DetectTextFromImg(ROI)
            txt_list = txt.splitlines()
            txt_list = list(filter(None, txt_list))
            if (len(txt_list)):
                txt = FindBestMatchString(TABLE_HEADER, txt_list)
                test = process.extract(TABLE_HEADER, [txt[:len(TABLE_HEADER)]])
                if (test[0][1] >= 85):
                    miny = pos['y'] + pos['h'] + 1
                    break
        #print(i)
        #print(cnt)
        prev_y = 0
        if (cnt == 0):
            return
        if (i < cnt):
            prev_y = pos_array[i]['y']
        while (i < cnt):
            pos = pos_array[i]
            if (pos['y'] >= item_y_max_pos):
                break
            table_row = []
            j = i
            while (j < cnt):
                pos = pos_array[j]
                #if (pos['y'] >= miny and pos['y'] + pos['h'] <= miny + TABLE_HEIGHT):
                if (abs(prev_y - pos['y']) <= 30 and pos['y'] <= item_y_max_pos and pos['y'] >= miny):
                    table_row.append(pos)
                    j += 1
                elif (abs(prev_y - pos['y']) > 30):
                    prev_y = pos['y']
                    break
                elif (pos['y'] < miny):
                    j += 1
                else:
                    break
                
            i = j
            # if (i < cnt):
            #     miny = pos_array[i]['y'] - THRESH
            # print(miny)
            if (len(table_row)):
                GetItemArea(table_row, original)
                table_row.clear()


        #cv2.imshow('image', image)
        cv2.imwrite('output/total1.png', image)
        #cv2.waitKey(0)
        # result.append({'items': item})

    FindingRectContours(filename)
    GetReferences(filename)
    print(result)
    print(item)

    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="reference_from_pdf"
    )

    mycursor = mydb.cursor()

    id = 0
    if ('company_name' in result):
        sql = "INSERT INTO customer_info (company_name, reference_name, street, city, ihr_ref, uns_ref) VALUES (%s, %s, %s, %s, %s, %s)"
        val = (result['company_name'], result['reference_name'], result['street'], result['city'], result['ihr_ref'], result['uns_ref'])

        mycursor.execute(sql, val)
        id = mycursor.lastrowid

    sql = "INSERT INTO items (item_no, item_desc, price, mwst, tot_price, customer_id) VALUES (%s, %s, %s, %s, %s, %s)"

    for itm in item:
        val = (itm['item_no'], itm['item_desc'], itm['price'], itm['mwst'], itm['totprice'], id)
        mycursor.execute(sql, val)

    mydb.commit()


    return result

#res_t = main('D:/DOSYA 16_10-03-2020-212729.pdf-142.png')
#res_t = main('D:/DOSYA 2_10-03-2020-195112.pdf-397.png')