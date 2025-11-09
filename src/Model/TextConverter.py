import string

class TextConverter():

    def __init__(self, fileName: str):
        self.text = ""
        self.lines = []
        self.words = []
        with open(fileName, 'r', encoding='utf-8') as f:
            self.text = f.read()
        self.to_lower()
        self.remove_punctuation()
        self.split_by_lines_and_by_words()

    def to_lower(self):
        self.text = self.text.lower()
        return self.text

    def remove_punctuation(self):
        self.text = ''.join(ch for ch in self.text if ch not in string.punctuation)
        return self.text

    def split_by_lines_and_by_words(self):
        lines = self.text.splitlines() # разделяю строки по '\n'
        for l in lines:
            if l != '':
                words = l.split() # разделяю на слова по ' '
                l=""
                for word in words:
                    self.words.append(word)
                    l += word + ' '
                self.lines.append(l.strip()) # Добавляю строку без лишних пробелов
                    

def main():
    a = TextConverter('test.txt')
    print(a.lines)
    print(a.words)

if __name__ == "__main__":
    main()