import pandas as pd
import re

class FoodDataProcessor:
    def __init__(self, file_path):
        self.df = pd.read_csv(file_path)
        
        # 식품대분류코드에 따른 평균밀도 설정
        self.liquid_codes = [4, 19, 20]
        self.solid_codes = [1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 22, 24, 25, 27]

        # 영양성분 attribute
        self.nutrient_columns = ['에너지(kcal)', '단백질(g)', '지방(g)', '탄수화물(g)', '당류(g)', '식이섬유(g)', '나트륨(mg)']

    def preprocess_data(self):
        # NULL값 처리 : 식품중량은 수작업, 영양성분은 0으로 처리
        self.df.fillna(0, inplace=True)
        
        # 'ml' to 'g' 변환 작업
        self.df['식품중량'] = self.df.apply(self.convert_weight, axis=1)
        
        # 영양성분 값들을 '식품중량'에 맞게 값 변환
        self.df = self.df.apply(self.adjust_nutrients_to_weight, axis=1)

    def convert_weight(self, row):
        weight_str = str(row['식품중량'])
        
        # 식품중량에서 숫자 출력
        weight_value = re.findall(r'\d+', weight_str)
        weight_value = float(weight_value[0]) if weight_value else 0  

        # 'ml'단위일 경우 조건 수행
        if 'ml' in weight_str:
            # 액체류 : 1 g/ml 
            if row['식품대분류코드'] in self.liquid_codes:
                return weight_value
            
            # 고체류 : 1.5 g/ml
            elif row['식품대분류코드'] in self.solid_codes:
                return weight_value * 1.5
        
        # 'g'단위일 경우 바로 반환
        return weight_value  

    def adjust_nutrients_to_weight(self, row):
        # 영양성분 기준량: 100g
        factor = row['식품중량'] / 100 
        
        # 값 변환 진행
        for column in self.nutrient_columns:
            row[column] = round(row[column] * factor, 2)
        
        return row

    def get_processed_data(self):
        return self.df