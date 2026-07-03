from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import StringProperty, BooleanProperty, ListProperty
import os
import re
import sys

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def parse_questions(filepath):
    questions = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        single_match = re.match(r'(\d+)\.\s*\(单选题', line)
        if single_match:
            q_num = int(single_match.group(1))
            q_text = re.sub(r'^\d+\.\s*\(单选题[^)]*\)\s*', '', line).strip()
            
            options = []
            j = i + 1
            answer = None
            while j < len(lines):
                raw_line = lines[j]
                opt_line = raw_line.strip()
                opt_match = re.match(r'^([A-D])\.(.*)', opt_line)
                if opt_match:
                    opt_text = opt_match.group(2).strip()
                    options.append(f"{opt_match.group(1)}. {opt_text}")
                    j += 1
                elif opt_line.startswith('正确答案'):
                    m = re.search(r'正确答案：([A-D])', opt_line)
                    if m:
                        answer = m.group(1)
                    i = j + 1
                    break
                elif opt_line:
                    q_text += ' ' + opt_line
                    j += 1
                else:
                    j += 1
            
            if answer is not None:
                questions.append({
                    'type': 'single',
                    'number': q_num,
                    'text': q_text,
                    'options': options,
                    'answer': answer
                })
                continue
        
        judge_match = re.match(r'(\d+)\.\s*\(判断题', line)
        if judge_match:
            q_num = int(judge_match.group(1))
            q_text = re.sub(r'^\d+\.\s*\(判断题[^)]*\)\s*', '', line).strip()
            
            j = i + 1
            answer = None
            while j < len(lines):
                ans_line = lines[j].strip()
                if ans_line.startswith('正确答案'):
                    m = re.search(r'正确答案：(对|错)', ans_line)
                    if m:
                        answer = m.group(1)
                    i = j + 1
                    break
                elif ans_line:
                    q_text += ' ' + ans_line
                j += 1
            
            if answer is not None:
                questions.append({
                    'type': 'judge',
                    'number': q_num,
                    'text': q_text,
                    'options': ['对', '错'],
                    'answer': answer
                })
                continue
        
        simple_single_match = re.match(r'(\d+)\.\s*(.+?)\s*$', line)
        if simple_single_match:
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ''
            if re.match(r'^[A-D]\.', next_line):
                q_num = int(simple_single_match.group(1))
                q_text = simple_single_match.group(2).strip()
                
                options = []
                j = i + 1
                answer = None
                while j < len(lines):
                    raw_line = lines[j]
                    opt_line = raw_line.strip()
                    opt_match = re.match(r'^([A-D])\.(.*)', opt_line)
                    if opt_match:
                        opt_text = opt_match.group(2).strip()
                        options.append(f"{opt_match.group(1)}. {opt_text}")
                        j += 1
                    elif opt_line.startswith('正确答案'):
                        m = re.search(r'正确答案：([A-D])', opt_line)
                        if m:
                            answer = m.group(1)
                        i = j + 1
                        break
                    else:
                        j += 1
                
                if answer is not None:
                    questions.append({
                        'type': 'single',
                        'number': q_num,
                        'text': q_text,
                        'options': options,
                        'answer': answer
                    })
                    continue
        
        i += 1
    
    return questions

class QuestionScreen(Screen):
    question_text = StringProperty("")
    progress_text = StringProperty("")
    score_text = StringProperty("")
    wrong_text = StringProperty("")
    result_text = StringProperty("")
    result_color = ListProperty([0, 0, 0, 1])
    is_answered = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super(QuestionScreen, self).__init__(**kwargs)
        self.current_file = None
        self.questions = []
        self.current_index = 0
        self.score = 0
        self.selected_answer = None
        self.wrong_questions = []
        self.is_review_mode = False
        self.review_wrong = []
        self.option_widgets = []
    
    def on_pre_enter(self):
        self.refresh_files()
    
    def refresh_files(self):
        base_path = get_base_path()
        txt_files = []
        try:
            for f in os.listdir(base_path):
                if f.lower().endswith('.txt'):
                    txt_files.append(f)
        except Exception:
            pass
        txt_files.sort()
        if txt_files:
            self.ids.file_spinner.values = txt_files
            if self.current_file and self.current_file in txt_files:
                self.ids.file_spinner.text = self.current_file
            else:
                self.ids.file_spinner.text = txt_files[0]
        else:
            self.ids.file_spinner.values = ["无文件"]
            self.ids.file_spinner.text = "无文件"
    
    def load_file(self, spinner, text):
        if text == "无文件":
            return
        filename = text
        filepath = os.path.join(get_base_path(), filename)
        if not os.path.exists(filepath):
            self.show_popup("错误", "文件不存在")
            return
        
        self.current_file = filename
        self.questions = parse_questions(filepath)
        
        if not self.questions:
            self.show_popup("警告", "未找到题目")
            return
        
        self.current_index = 0
        self.score = 0
        self.wrong_questions = []
        self.is_review_mode = False
        self.review_wrong = []
        self.ids.mode_label.text = ""
        self.update_score()
        self.update_wrong_count()
        self.show_question()
    
    def show_question(self):
        if not self.questions:
            return
        
        self.is_answered = False
        self.selected_answer = None
        self.result_text = ""
        self.result_color = [0, 0, 0, 1]
        
        self.ids.confirm_btn.disabled = False
        self.ids.prev_btn.disabled = (self.current_index == 0)
        self.ids.next_btn.disabled = (self.current_index >= len(self.questions) - 1)
        
        question = self.questions[self.current_index]
        
        if question['type'] == 'single':
            q_type = "单选题"
        else:
            q_type = "判断题"
        
        mode_text = "【错题重做】" if self.is_review_mode else ""
        self.question_text = f"第 {question['number']} 题 ({q_type}) {mode_text}\n\n{question['text']}"
        
        for widget in self.option_widgets:
            self.ids.options_box.remove_widget(widget)
        self.option_widgets.clear()
        
        for i, option in enumerate(question['options']):
            btn = Button(
                text=option,
                size_hint_y=None,
                height=dp(50),
                font_size=dp(16),
                background_color=[0.95, 0.95, 0.95, 1],
                color=[0, 0, 0, 1],
                on_release=lambda b, idx=i: self.select_option(idx)
            )
            self.ids.options_box.add_widget(btn)
            self.option_widgets.append(btn)
        
        self.progress_text = f"进度: {self.current_index + 1}/{len(self.questions)}"
    
    def select_option(self, idx):
        if self.is_answered:
            return
        self.selected_answer = idx
        for i, btn in enumerate(self.option_widgets):
            if i == idx:
                btn.background_color = [0.3, 0.6, 1, 1]
                btn.color = [1, 1, 1, 1]
            else:
                btn.background_color = [0.95, 0.95, 0.95, 1]
                btn.color = [0, 0, 0, 1]
    
    def confirm_answer(self):
        if self.is_answered:
            return
        if self.selected_answer is None:
            self.show_popup("警告", "请选择一个答案")
            return
        
        self.is_answered = True
        self.ids.confirm_btn.disabled = True
        
        for btn in self.option_widgets:
            btn.disabled = True
        
        question = self.questions[self.current_index]
        
        if question['type'] == 'single':
            user_answer = chr(ord('A') + int(self.selected_answer))
        else:
            user_answer = question['options'][int(self.selected_answer)]
        
        is_correct = (user_answer == question['answer'])
        
        if is_correct:
            self.result_text = f"✓ 回答正确！正确答案: {question['answer']}"
            self.result_color = [0, 0.7, 0, 1]
            self.score += 1
            self.update_score()
            delay = 0.5
        else:
            self.result_text = f"✗ 回答错误！你的答案: {user_answer}  正确答案: {question['answer']}"
            self.result_color = [0.9, 0, 0, 1]
            if self.is_review_mode:
                self.review_wrong.append(question)
            else:
                self.wrong_questions.append(question)
            self.update_wrong_count()
            delay = 1.0
        
        if self.current_index < len(self.questions) - 1:
            Clock.schedule_once(lambda dt: self.auto_next(), delay)
        else:
            Clock.schedule_once(lambda dt: self.finish_quiz(), delay)
    
    def auto_next(self):
        if self.current_index < len(self.questions) - 1:
            self.current_index += 1
            self.show_question()
    
    def next_question(self):
        if self.is_answered:
            return
        if self.current_index < len(self.questions) - 1:
            self.current_index += 1
            self.show_question()
    
    def prev_question(self):
        if self.is_answered:
            return
        if self.current_index > 0:
            self.current_index -= 1
            self.show_question()
    
    def finish_quiz(self):
        total = len(self.questions)
        if self.is_review_mode:
            if self.review_wrong:
                wrong_count = len(self.review_wrong)
                content = BoxLayout(orientation='vertical', padding=20)
                content.add_widget(Label(text=f"本次重做完成！\n得分: {self.score}/{total}\n仍有 {wrong_count} 道错题", font_size=dp(18)))
                btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=10)
                yes_btn = Button(text="再次重做", on_release=lambda b: (popup.dismiss(), self.start_review()))
                no_btn = Button(text="返回", on_release=lambda b: popup.dismiss())
                btn_box.add_widget(yes_btn)
                btn_box.add_widget(no_btn)
                content.add_widget(btn_box)
                popup = Popup(title="错题重做完成", content=content, size_hint=(0.8, 0.6))
                popup.open()
            else:
                self.show_popup("错题重做完成", f"恭喜！全部错题已答对！\n得分: {self.score}/{total}")
            self.is_review_mode = False
            self.ids.mode_label.text = ""
            self.ids.review_btn.disabled = (len(self.wrong_questions) == 0)
        else:
            wrong_count = len(self.wrong_questions)
            msg = f"测验完成！\n总得分: {self.score}/{total}\n错题数: {wrong_count}"
            if wrong_count > 0:
                msg += "\n\n可以点击「错题重做」来复习错题"
                self.ids.review_btn.disabled = False
            self.show_popup("完成", msg)
    
    def start_review(self):
        if not self.wrong_questions:
            self.show_popup("提示", "没有错题需要重做！")
            return
        
        self.is_review_mode = True
        self.ids.mode_label.text = "【错题重做模式】"
        self.questions = list(self.wrong_questions)
        self.wrong_questions = []
        self.review_wrong = []
        self.current_index = 0
        self.score = 0
        self.update_score()
        self.update_wrong_count()
        self.ids.review_btn.disabled = True
        self.show_question()
    
    def show_overview(self):
        if not self.questions:
            return
        
        overview_screen = self.manager.get_screen('overview')
        overview_screen.load_questions(self.questions, self.current_index)
        self.manager.current = 'overview'
    
    def update_score(self):
        self.score_text = f"得分: {self.score}"
    
    def update_wrong_count(self):
        count = len(self.review_wrong) if self.is_review_mode else len(self.wrong_questions)
        self.wrong_text = f"错题: {count}"
    
    def restart_quiz(self):
        if self.current_file:
            self.load_file(None, self.current_file)
    
    def show_popup(self, title, text):
        content = BoxLayout(orientation='vertical', padding=20)
        content.add_widget(Label(text=text, font_size=dp(18)))
        content.add_widget(Button(text="确定", size_hint_y=None, height=dp(50),
                                  on_release=lambda b: popup.dismiss()))
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.6))
        popup.open()

class OverviewScreen(Screen):
    def __init__(self, **kwargs):
        super(OverviewScreen, self).__init__(**kwargs)
        self.questions = []
        self.current_index = 0
    
    def load_questions(self, questions, current_index):
        self.questions = questions
        self.current_index = current_index
        
        self.ids.question_list.clear_widgets()
        
        for idx, q in enumerate(questions):
            q_type = "单选" if q['type'] == 'single' else "判断"
            preview = q['text'][:30] + "..." if len(q['text']) > 30 else q['text']
            item = Button(
                text=f"第{q['number']}题 ({q_type})\n{preview}",
                size_hint_y=None,
                height=dp(70),
                font_size=dp(14),
                background_color=[0.3, 0.6, 1, 1] if idx == current_index else [0.95, 0.95, 0.95, 1],
                color=[1, 1, 1, 1] if idx == current_index else [0, 0, 0, 1],
                on_release=lambda b, i=idx: self.jump_to(i)
            )
            self.ids.question_list.add_widget(item)
        
        self.ids.info_label.text = f"共 {len(questions)} 道题"
    
    def jump_to(self, idx):
        question_screen = self.manager.get_screen('question')
        question_screen.current_index = idx
        question_screen.show_question()
        self.manager.current = 'question'
    
    def go_back(self):
        self.manager.current = 'question'

class QuizReviewerApp(App):
    def build(self):
        sm = ScreenManager()
        
        question_screen = QuestionScreen(name='question')
        sm.add_widget(question_screen)
        
        overview_screen = OverviewScreen(name='overview')
        sm.add_widget(overview_screen)
        
        return sm

if __name__ == '__main__':
    QuizReviewerApp().run()