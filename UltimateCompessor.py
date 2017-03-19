# -*- coding: utf-8 -*-
import pygame, os, sys, random, time
from pygame.locals import *
from io import StringIO

pygame.init()
display_width = 1280
display_height = 720
gameDisplay = pygame.display.set_mode((display_width, display_height))
pygame.display.set_caption('Ultimate Compressor')
ico = pygame.image.load('ico.bmp')
pygame.display.set_icon(ico)
white = (255, 255, 255)
black = (0, 0, 0)
gray = (205, 205, 205)
red = (255, 0, 0)
yellow = (255, 255, 0)
green = (0, 100, 0)
blue = (0, 0, 255)
FPS = 15
FPSClock = pygame.time.Clock()
smallfont = pygame.font.SysFont("Courier", 25)
medfont = pygame.font.SysFont("comicsansms", 50)
largefont = pygame.font.SysFont("comicsansms", 85)
codefont = pygame.font.SysFont("Courier", 20)
copyrfont = pygame.font.SysFont("comicsansms", 18)
pygame.mixer.music.load("music/misletoe.ogg")
pygame.mixer.music.play(-1)


def text_objects(text, color, size="small"):
    if size == "small":
        textSurface = smallfont.render(text, True, color)
    if size == "medium":
        textSurface = medfont.render(text, True, color)
    if size == "large":
        textSurface = largefont.render(text, True, color)
    if size == "code":
        textSurface = codefont.render(text, True, color)
    return textSurface, textSurface.get_rect()


def message_to_screen(msg, color, y_displace=0, size="small"):
    textSurf, textRect = text_objects(msg, color, size)
    textRect.center = (int(display_width / 2), int(display_height / 2) + y_displace)
    gameDisplay.blit(textSurf, textRect)


class RLE:
    def encode(self, picture):
        count = 1
        pic = ""
        for i, colour in enumerate(picture):
            try:
                if colour == picture[i + 1] and count < 9:
                    count = count + 1
                else:
                    if count == 1:
                        pic += str(colour)
                    else:
                        pic += str(count)
                        pic += str(colour)
                    count = 1
            except IndexError:
                if count == 1:
                    pic += str(colour)
                else:
                    pic += str(count)
                    pic += str(colour)
        return pic

    def decode(self, picture):
        pic = ""
        count = 1
        for colour in picture:
            try:
                float(colour)
                count = int(colour)
            except ValueError:
                pic += str(count * colour)
                count = 1
        return pic


class LZ77:
    def __init__(self):
        self.referencePrefix = "`"
        self.referencePrefixCode = ord(self.referencePrefix)
        self.referenceIntBase = 96
        self.referenceIntFloorCode = ord(" ")
        self.referenceIntCeilCode = self.referenceIntFloorCode + self.referenceIntBase - 1
        self.maxStringDistance = self.referenceIntBase ** 2 - 1
        self.minStringLength = 5
        self.maxStringLength = self.referenceIntBase ** 1 - 1 + self.minStringLength
        self.maxWindowLength = self.maxStringDistance + self.minStringLength;
        self.defaultWindowLength = 144

    def encode(self, data, windowLength=None):
        if windowLength == None:
            windowLength = self.defaultWindowLength
        compressed = ""
        pos = 0
        lastPos = len(data) - self.minStringLength
        while pos < lastPos:
            searchStart = max(pos - windowLength, 0);
            matchLength = self.minStringLength
            foundMatch = False
            bestMatchDistance = self.maxStringDistance
            bestMatchLength = 0
            while (searchStart + matchLength) < pos:
                m1 = data[searchStart: searchStart + matchLength]
                m2 = data[pos: pos + matchLength]
                isValidMatch = (m1 == m2 and matchLength < self.maxStringLength)
                if isValidMatch:
                    matchLength += 1
                    foundMatch = True
                else:
                    realMatchLength = matchLength - 1
                    if foundMatch and realMatchLength > bestMatchLength:
                        bestMatchDistance = pos - searchStart - realMatchLength
                        bestMatchLength = realMatchLength
                    matchLength = self.minStringLength
                    searchStart += 1
                    foundMatch = False
            if bestMatchLength:
                newCompressed = (
                    self.referencePrefix + self.__encodeReferenceInt(bestMatchDistance,
                                                                     2) + self.__encodeReferenceLength(
                        bestMatchLength))
                pos += bestMatchLength
            else:
                if data[pos] != self.referencePrefix:
                    newCompressed = data[pos]
                else:
                    newCompressed = self.referencePrefix + self.referencePrefix
                pos += 1
            compressed += newCompressed
        return compressed + data[pos:].replace("`", "``")

    def decode(self, data):
        decompressed = ""
        pos = 0
        while pos < len(data):
            currentChar = data[pos]
            if currentChar != self.referencePrefix:
                decompressed += currentChar
                pos += 1
            else:
                nextChar = data[pos + 1]
                if nextChar != self.referencePrefix:
                    distance = self.__decodeReferenceInt(data[pos + 1: pos + 3], 2)
                    length = self.__decodeReferenceLength(data[pos + 3])
                    start = len(decompressed) - distance - length
                    end = start + length
                    decompressed += decompressed[start: end]
                    pos += self.minStringLength - 1
                else:
                    decompressed += self.referencePrefix
                    pos += 2
        return decompressed

    def __encodeReferenceInt(self, value, width):
        encoded = ""
        while value > 0:
            encoded = chr((value % self.referenceIntBase) + self.referenceIntFloorCode) + encoded
            value = int(value / self.referenceIntBase)
        missingLength = width - len(encoded)
        for i in range(missingLength):
            encoded = chr(self.referenceIntFloorCode) + encoded
        return encoded

    def __encodeReferenceLength(self, length):
        return self.__encodeReferenceInt(length - self.minStringLength, 1)

    def __decodeReferenceInt(self, data, width):
        value = 0
        for i in range(width):
            value *= self.referenceIntBase
            charCode = ord(data[i])
            if charCode >= self.referenceIntFloorCode and charCode <= self.referenceIntCeilCode:
                value += charCode - self.referenceIntFloorCode
            else:
                raise Exception("Invalid char code: %d" % charCode)
        return value

    def __decodeReferenceLength(self, data):
        return self.__decodeReferenceInt(data, 1) + self.minStringLength


class LZW:
    def encode(self, uncompressed):
        dict_size = 256
        dictionary = {chr(i): chr(i) for i in range(dict_size)}
        w = ""
        result = []
        for c in uncompressed:
            wc = w + c
            if wc in dictionary:
                w = wc
            else:
                result.append(dictionary[w])
                dictionary[wc] = dict_size
                dict_size += 1
                w = c
        if w:
            result.append(dictionary[w])
        return result

    def decode(self, compressed):
        dict_size = 256
        dictionary = {chr(i): chr(i) for i in range(dict_size)}
        result = StringIO()
        w = compressed.pop(0)
        result.write(w)
        for i in compressed:
            if i in dictionary:
                entry = dictionary[i]
            elif i == dict_size:
                entry = w + w[0]
            result.write(entry)
            dictionary[dict_size] = w + entry[0]
            dict_size += 1
            w = entry
        return result.getvalue()


def Intro():
    print("UltimateCompressor \n")
    pmpu = pygame.image.load("images/pmpu.jpg")
    intro = True
    while intro:
        gameDisplay.fill(white)
        gameDisplay.blit(pmpu, (display_width-500, display_height-700))
        message_to_screen("Ultimate Compressor", green, -200, size="large")
        message_to_screen("Нажмите ENTER, чтобы начать демонстрацию", black, -30)
        message_to_screen("Нажмите 1, чтобы перейти к RLE", black, 10)
        message_to_screen("Нажмите 2, чтобы перейти к LZ77", black, 50)
        message_to_screen("Нажмите 3, чтобы перейти к LZW", black, 90)
        message_to_screen("Нажмите ESCAPE, чтобы выйти", black, 300)
        gameDisplay.blit(copyrfont.render("Джумабаев Имран, 308 группа, 2016 г.", True, black), (10, display_height-25))
        pygame.display.update()
        FPSClock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1 or event.key == pygame.K_RETURN:
                    intro = False
                    RLEshowtime()
                elif event.key == pygame.K_2:
                    intro = False
                    LZ77showtime()
                elif event.key == pygame.K_3:
                    intro = False
                    LZWshowtime()
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()


def RLEshowtime():
    print("RLE")
    notready = True
    while notready:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    notready = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()
        gameDisplay.fill(white)
        message_to_screen("RLE", green, -200, size="large")
        message_to_screen("Данная программа демонстрирует алгоритм сжатия данных RLE на примере особого", black, -30)
        message_to_screen("формата чёрно-белых изображений, являющих собой строку из ста символов W или B", black, 10)
        message_to_screen("Эти 100 символов делятся на 10 строк по 10 символов. Каждый символ преобразуется в", black,
                          50)
        message_to_screen("пиксель соответствующего цвета. Пожалуйста, найдите в папке examples файл", black, 90)
        message_to_screen("rle_input.txt. При желании вы можете отредактировать его.", black, 130)
        message_to_screen("ENTER - продолжить, ESCAPE - выйти", black, 300)
        pygame.display.update()
        FPSClock.tick(FPS)
    rle_input = open("examples/rle_input.txt", 'r')
    picture = rle_input.read()
    rle_input.close()
    showpicture = True
    while showpicture:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    showpicture = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()
        gameDisplay.fill(gray)
        message_to_screen("Наше исходное изображение выглядит так: ", blue, -300, size="medium")
        for i in range(len(picture)):
            if picture[i] == 'B':
                pygame.draw.rect(gameDisplay, black, (515 + (i % 10) * 25, 200 + (i // 10) * 25, 25, 25))
            elif picture[i] == 'W':
                pygame.draw.rect(gameDisplay, white, (515 + (i % 10) * 25, 200 + (i // 10) * 25, 25, 25))
        message_to_screen("rle_input.txt", green, 160, size="code")
        message_to_screen(picture, green, 200, size="code")
        message_to_screen("ENTER - продолжить, ESCAPE - выйти", black, 300)
        pygame.display.update()
        FPSClock.tick(FPS)
    print(picture)
    rle_compressed = open("examples/rle_compressed.txt", 'w')
    rle_decompressed = open("examples/rle_decompressed.txt", 'w')
    rle = RLE()
    picture_compressed = rle.encode(picture)
    picture_decompressed = rle.decode(picture_compressed)
    print(picture_compressed)
    print(picture_decompressed)
    rle_compressed.write(picture_compressed)
    rle_decompressed.write(picture_decompressed)
    rle_compressed.close()
    rle_decompressed.close()
    efficiency = len(picture_decompressed) / len(picture_compressed)
    print("len(picture_decompressed) / len(picture_compressed) =", efficiency, "\n")
    efficiency_msg = "Мы смогли сжать наш файл в " + str(efficiency) + " раз"
    showresult = True
    while showresult:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    showresult = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()
        gameDisplay.fill(white)
        message_to_screen("До сжатия наш файл выглядел так: ", black, -300, size="medium")
        message_to_screen(picture, green, -220, size="code")
        message_to_screen("После сжатия: ", black, -100, size="medium")
        message_to_screen(picture_compressed, green, -20, size="code")
        message_to_screen(efficiency_msg, black, 100)
        message_to_screen("ENTER - продолжить, ESCAPE - выйти", black, 300)
        pygame.display.update()
        FPSClock.tick(FPS)
    showresult2 = True
    while showresult2:
        gameDisplay.fill(white)
        message_to_screen("rle_input.txt: ", black, -300, size="code")
        message_to_screen(picture, green, -270, size="code")
        message_to_screen("rle_compressed: ", black, -220, size="code")
        message_to_screen(picture_compressed, green, -190, size="code")
        message_to_screen("rle_decompressed: ", black, -140, size="code")
        message_to_screen(picture_decompressed,
                          green, -110, size="code")
        message_to_screen("rle_compressed.txt и rle_decompressed.txt можно найти в папке examples", black, 100,
                          size="code")
        message_to_screen("ENTER - продолжить, ESCAPE - выйти", black, 300)
        pygame.display.update()
        FPSClock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    showresult2 = False
                    LZ77showtime()
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()


def LZ77showtime():
    print("LZ77")
    notready = True
    while notready:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    notready = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()
        gameDisplay.fill(white)
        message_to_screen("LZ77", green, -200, size="large")
        message_to_screen("Данная программа демонстрирует алгоритм сжатия данных LZ77 на примере обычного", black, -30)
        message_to_screen("текстового файла. Пожалуйста, найдите в папке examples файл lz77_input.txt", black, 10)
        message_to_screen("При желании вы можете отредактировать его.", black, 50)
        message_to_screen("ENTER - продолжить, ESCAPE - выйти", black, 300)
        pygame.display.update()
        FPSClock.tick(FPS)
    lz77_input = open("examples/lz77_input.txt", 'r')
    textfile = lz77_input.read()
    lz77_input.close()
    showtextfile = True
    while showtextfile:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    showtextfile = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()
        gameDisplay.fill(gray)
        message_to_screen("Наш исходный текстовый файл выглядит так: ", blue, -300, size="medium")
        message_to_screen("lz77_input.txt", green, -200, size="code")
        message_to_screen(textfile, green, -100, size="code")
        message_to_screen("ENTER - продолжить, ESCAPE - выйти", black, 300)
        pygame.display.update()
        FPSClock.tick(FPS)
    print(textfile)
    lz77_compressed = open("examples/lz77_compressed.txt", 'w')
    lz77_decompressed = open("examples/lz77_decompressed.txt", 'w')
    lz77 = LZ77()
    textfile_compressed = lz77.encode(textfile)
    textfile_decompressed = lz77.decode(textfile_compressed)
    print(textfile_compressed)
    print(textfile_decompressed)
    lz77_compressed.write(textfile_compressed)
    lz77_decompressed.write(textfile_decompressed)
    lz77_compressed.close()
    lz77_decompressed.close()
    beforesize = str(os.path.getsize("examples/lz77_input.txt")) + " байт"
    aftersize = str(os.path.getsize("examples/lz77_compressed.txt")) + " байт"
    efficiency = os.path.getsize("examples/lz77_input.txt") / os.path.getsize("examples/lz77_compressed.txt")
    print("size_before / size_after =", efficiency, "\n")
    efficiency_msg = "Мы смогли сжать наш файл в " + str(efficiency) + " раз"
    showresult = True
    while showresult:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    showresult = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()
        gameDisplay.fill(white)
        message_to_screen("До сжатия наш файл имел размер: ", black, -300, size="medium")
        message_to_screen(beforesize, red, -220, size="medium")
        message_to_screen("После сжатия: ", black, -100, size="medium")
        message_to_screen(aftersize, red, -20, size="medium")
        message_to_screen(efficiency_msg, black, 100)
        message_to_screen("ENTER - продолжить, ESCAPE - выйти", black, 300)
        pygame.display.update()
        FPSClock.tick(FPS)
    showresult2 = True
    while showresult2:
        gameDisplay.fill(white)
        message_to_screen("lz77_input.txt: ", black, -300, size="code")
        message_to_screen(textfile, green, -270, size="code")
        message_to_screen("lz77_compressed: ", black, -220, size="code")
        message_to_screen(textfile_compressed, green, -190, size="code")
        message_to_screen("lz77_decompressed: ", black, -140, size="code")
        message_to_screen(textfile_decompressed,
                          green, -110, size="code")
        message_to_screen("lz77_compressed.txt и lz77_decompressed.txt можно найти в папке examples", black, 100,
                          size="code")
        message_to_screen("ENTER - продолжить, ESCAPE - выйти", black, 300)
        pygame.display.update()
        FPSClock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    showresult2 = False
                    LZWshowtime()
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()


def LZWshowtime():
    print("LZW")
    notready = True
    while notready:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    notready = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()
        gameDisplay.fill(white)
        message_to_screen("LZW", green, -200, size="large")
        message_to_screen("Данная программа демонстрирует алгоритм сжатия данных LZW на примере", black, -30)
        message_to_screen("текста. Пожалуйста, найдите в папке examples файл lzw_input.txt", black, 10)
        message_to_screen("При желании вы можете отредактировать его.", black, 50)
        message_to_screen("ENTER - продолжить, ESCAPE - выйти", black, 300)
        pygame.display.update()
        FPSClock.tick(FPS)
    lzw_input = open("examples/lzw_input.txt", 'r')
    quote = lzw_input.read()
    lzw_input.close()
    showquote = True
    while showquote:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    showquote = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()
        gameDisplay.fill(gray)
        message_to_screen("Наш исходный текст выглядит так: ", blue, -300, size="medium")
        message_to_screen("lzw_input.txt", green, -200, size="code")
        message_to_screen(quote, green, -100, size="code")
        message_to_screen("ENTER - продолжить, ESCAPE - выйти", black, 300)
        pygame.display.update()
        FPSClock.tick(FPS)
    print(quote)
    lzw_compressed = open("examples/lzw_compressed.txt", 'w')
    lzw_decompressed = open("examples/lzw_decompressed.txt", 'w')
    lzw = LZW()
    quote_compressed = lzw.encode(quote)
    print(quote_compressed)
    compressed_quote = str(quote_compressed)
    quote_decompressed = lzw.decode(quote_compressed)
    print(quote_decompressed)
    lzw_compressed.write(compressed_quote)
    lzw_decompressed.write(quote_decompressed)
    lzw_compressed.close()
    lzw_decompressed.close()
    beforewords = str(len(quote)) + " слов"
    afterwords = str(len(quote_compressed)+1) + " слов"
    efficiency = len(quote) / (len(quote_compressed)+1)
    efficiency_msg = "K / D = " + str(efficiency)
    print("len(quote) / len(quote_compressed =", efficiency, "\n")
    words_compressed = compressed_quote
    showresult = True
    while showresult:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    showresult = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()
        gameDisplay.fill(white)
        message_to_screen("До сжатия наш текст состоял из: ", black, -300, size="medium")
        message_to_screen(beforewords, red, -220, size="medium")
        message_to_screen("После сжатия: ", black, -100, size="medium")
        message_to_screen(afterwords, red, -20, size="medium")
        message_to_screen(efficiency_msg, black, 100)
        message_to_screen("ENTER - продолжить, ESCAPE - выйти", black, 300)
        pygame.display.update()
        FPSClock.tick(FPS)
    showresult2 = True
    while showresult2:
        gameDisplay.fill(white)
        message_to_screen("lzw_input.txt: ", black, -300, size="code")
        message_to_screen(quote, green, -270, size="code")
        message_to_screen("lzw_compressed: ", black, -220, size="code")
        message_to_screen(words_compressed, green, -190, size="code")
        message_to_screen("lzw_decompressed: ", black, -140, size="code")
        message_to_screen(quote_decompressed,
                          green, -110, size="code")
        message_to_screen("lzw_compressed.txt и lzw_decompressed.txt можно найти в папке examples", black, 100,
                          size="code")
        message_to_screen("ENTER - продолжить, ESCAPE - выйти", black, 300)
        pygame.display.update()
        FPSClock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    showresult2 = False
                    theend()
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()


def theend():
    pmpu = pygame.image.load("images/pmpu.jpg")
    end = pygame.image.load("images/end.jpg")
    thisistheend = True
    while thisistheend:
        gameDisplay.fill(white)
        gameDisplay.blit(pmpu, (display_width-500, display_height-700))
        gameDisplay.blit(end, (display_width/2-300, display_height/2-200))
        message_to_screen("Спасибо за внимание!", green, -300, size="large")
        message_to_screen("Нажмите ESCAPE, чтобы выйти", black, 300)
        gameDisplay.blit(copyrfont.render("Джумабаев Имран, 308 группа, 2016 г.", True, black), (10, display_height-25))
        pygame.display.update()
        FPSClock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()


Intro()
