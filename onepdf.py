from pdf2image import convert_from_path
import get_one_page_result
import os

def convert_pdf_to_images(pdf_path):
    for i in range(1, 1000):
        print(i)
        images = convert_from_path(pdf_path, dpi=184.3, poppler_path=r"E:\AI\poppler-0.68.0\bin", first_page=i , last_page=i)
        if (len(images) == 0):
            break;
        print((len(images)))
        # print(images)
        for index, image in enumerate(images):
            image.save(f'output/{pdf_path}-{index}.png')
            get_one_page_result.main(f'output/{pdf_path}-{index}.png')
            # image.save(f'output/1.png')
            # get_one_page_result.main(f'output/1.png')

entries = os.listdir('resource/')
for entry in entries:
    #print(entry)
    #os.rename('resource/'+entry, 'done/'+entry)
    convert_pdf_to_images('resource/' + entry)

# pdfFileObj = open('DOSYA 1_10-02-2020-004404.pdf', 'rb')
# pdfReader = PyPDF2.PdfFileReader(pdfFileObj)

# print(pdfReader.numPages)

# pageObj = pdfReader.getPage(0)
# print(pageObj.getPixmap().writePNG('1.png'))

# pdfFileObj.close()