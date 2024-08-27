# Mengimpor Pustaka
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd
import numpy as np
import time

class WebscrapeSamsatJabar:
    def __init__(self, 
                 df_prewebscrape: pd.core.frame.DataFrame, 
                 web, 
                 col_names_to_scrape, 
                 chrome_driver_path, 
                 buster_path,
                 filename = ['Data Plat Jabar.xlsx'],
                 main_sheetname =['Jabar'],
                 error_sheetname = ['Error'],
                 df_postwebscrape:pd.core.frame.DataFrame = None,
                 df_failedwebscrape:pd.core.frame.DataFrame = None) -> None:
        
        """Set Up Data Before and After Webscraping"""
        self.df_prewebscrape = df_prewebscrape
        if df_postwebscrape.empty == True:
            self.df_postwebscrape = pd.DataFrame(columns=col_names_to_scrape)
        else:
            self.df_postwebscrape = df_postwebscrape
            self.df_postwebscrape.drop_duplicates(inplace=True)
        if df_failedwebscrape.empty == True:
            self.df_failedwebscrape = pd.DataFrame(columns=['plate','error'])
        else:
            self.df_failedwebscrape = df_failedwebscrape

        """Set Up Chrome Driver"""
        self.buster_path = buster_path
        self.chrome_driver_path = chrome_driver_path
        self.web = web

        """Set Up Exported File"""
        self.filename = filename
        self.main_sheetname = main_sheetname
        self.error_sheetname = error_sheetname

        return None
    
    def settingup_driver(self):
        """Set Up Chrome Driver"""
        options = Options()
        options.add_argument("--start-maximized") 
        options.add_extension(self.buster_path)
        service = Service(executable_path=self.chrome_driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    
    def export_plat_jabar(self, soup):
        """Extract data from the webpage using BeautifulSoup"""
        raw_source = soup.find_all('div', class_='border rounded-xl px-3 py-4')
        titles = []
        contents = []
        for raw_idx in range(len(raw_source)-1):
            id_source = raw_source[raw_idx]
            informasi_kendaraan_source = id_source.find_all('div', class_='flex flex-col')
            for idx in range(len(informasi_kendaraan_source)):
                titles.append(informasi_kendaraan_source[idx].find('p', class_='text-sm text-[#757575]').text.strip())
                contents.append(informasi_kendaraan_source[idx].find('h2', class_='text-sm font-semibold').text.strip())
        table_target = raw_source[2].find('table', class_='w-full text-sm')
        info_biaya_source = table_target.find_all('tr')
        for idx in range(len(info_biaya_source)):
            titles.append(info_biaya_source[idx].find_all('td')[0].text.strip())
            contents.append(info_biaya_source[idx].find_all('td')[2].text.strip())
        """Create a dictionary for DataFrame"""
        row_dict = dict(zip(titles, contents))

        """Convert to DataFrame"""
        return pd.DataFrame([row_dict])

    def click_buster(self, driver):
        """Click the buster on reCAPTCHA"""
        shadow_host_locator = (By.XPATH, '//div[@class="button-holder help-button-holder"]')
        shadow_host = WebDriverWait(driver, np.random.randint(10)).until(EC.element_to_be_clickable(shadow_host_locator))
        shadow_host.click()
        action = ActionChains(driver)
        action.send_keys(Keys.ENTER).perform()  # Press Enter to activate the button

    def webscraping(self,
                    df,
                    nopol_col_id,
                    kodedepan_col_id,
                    kodetengah_col_id,
                    kodebelakang_col_id,
                    step=50):
        """Perform webscraping of data from the webpage"""
        faileds = []
        iter_range = np.round(np.linspace(0, df.shape[0], step+1)).astype(int)
        try:
            for iter in range(len(iter_range)-1):
                driver = self.settingup_driver()
                driver.get(self.web)
                error_count = 0
                with tqdm(total=iter_range[iter+1]-iter_range[iter], 
                        desc=f"Processing (Index: {iter_range[iter]} -> {iter_range[iter+1]-1})", 
                        postfix={"errors": error_count}) as pbar:
                    for idx_plat in tqdm(range(iter_range[iter], iter_range[iter+1])): # df.shape[0]
                        try:
                            individual_data = df.loc[[idx_plat]].to_numpy().flatten()

                            driver.switch_to.default_content()

                            iframe1 = (By.XPATH, '//*[@id="main"]/div/div/main/div/div/section/div/div/iframe') # Main Content Frame

                            WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it(iframe1))

                            driver.find_element(By.XPATH, '//*[@id="root"]/main/div[1]/section[2]/div/input[1]').send_keys(individual_data[kodedepan_col_id])
                            driver.find_element(By.XPATH, '//*[@id="root"]/main/div[1]/section[2]/div/input[2]').send_keys(individual_data[kodetengah_col_id])
                            driver.find_element(By.XPATH, '//*[@id="root"]/main/div[1]/section[2]/div/input[3]').send_keys(individual_data[kodebelakang_col_id])

                            try:
                                iframe2 = (By.XPATH, ".//iframe[@title='reCAPTCHA']") # Recaptcha Title Box

                                WebDriverWait(driver, 10).until(
                                    EC.frame_to_be_available_and_switch_to_it(iframe2)
                                    )

                                # Click the reCAPTCHA checkbox
                                recaptcha_checkbox = WebDriverWait(driver, np.random.randint(10)).until(
                                    EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))
                                    )
                                recaptcha_checkbox.click()
                                time.sleep(1)
                                driver.switch_to.default_content()
                                WebDriverWait(driver, 4).until(EC.frame_to_be_available_and_switch_to_it(iframe1))
                                time.sleep(1)
                                driver.find_element(By.XPATH, '//*[@id="root"]/main/div[1]/button').click()

                            except:
                                driver.switch_to.default_content()
                                WebDriverWait(driver, np.random.randint(4,10)).until(EC.frame_to_be_available_and_switch_to_it(iframe1))
                                
                                iframe3 = (By.XPATH, ".//iframe[@title='recaptcha challenge expires in two minutes']") # Recaptcha Challenge Box
                                WebDriverWait(driver, np.random.randint(4,10)).until(EC.frame_to_be_available_and_switch_to_it(iframe3))

                                try:
                                    self.click_buster(driver=driver)
                                except:
                                    try:
                                        self.click_buster(driver=driver)
                                    except:
                                        try:
                                            self.click_buster(driver=driver)
                                        except Exception as e:
                                            faileds.append([df.iloc[idx_plat, nopol_col_id], e])
                                            pass

                                driver.switch_to.default_content()
                                WebDriverWait(driver, 4).until(EC.frame_to_be_available_and_switch_to_it(iframe1))
                                time.sleep(3)
                                driver.find_element(By.XPATH, '//*[@id="root"]/main/div[1]/button').click()
                                time.sleep(3)
                            finally:
                                try:
                                    WebDriverWait(driver, 6).until(EC.text_to_be_present_in_element((By.XPATH, '//h2[@class="text-base font-bold"]'), 'Informasi Kendaraan'))
                                except TimeoutException as e:
                                    faileds.append([df.iloc[idx_plat, nopol_col_id], e])
                                page_source = driver.page_source
                                soup = BeautifulSoup(page_source, 'html.parser')
                                individual_plat = self.export_plat_jabar(soup)
                                self.df_postwebscrape = pd.concat([self.df_postwebscrape, individual_plat])

                        except Exception as e:
                            faileds.append([df.iloc[idx_plat, nopol_col_id], e])
                            error_count += 1
                            pbar.set_postfix(errors=error_count)  # Update postfix with the current error count
                            pbar.update(1)
                            driver.get(self.web)
                            continue
                        driver.get(self.web)
                        time.sleep(1)
                        if len(faileds) != 0:
                            failed_arr = np.array(faileds)
                        else:
                            failed_arr = np.array([[np.nan, np.nan]])
                        df_failed = pd.DataFrame(data={'plate': failed_arr[:, 0], 'error': failed_arr[:, 1]})
                        self.df_failedwebscrape = pd.concat([self.df_failedwebscrape, df_failed])
                        self.df_failedwebscrape.reset_index(drop=True, inplace=True)
                        self.df_postwebscrape.reset_index(drop=True, inplace=True)

                        with pd.ExcelWriter(self.filename, engine='openpyxl') as writer:
                            self.df_postwebscrape.to_excel(writer, sheet_name=self.main_sheetname, index=False)
                            self.df_failedwebscrape.to_excel(writer, sheet_name=self.error_sheetname, index=False)

                        pbar.update(1)  # Update the progress bar
                # Close driver
                driver.quit()
        except Exception as e:
            print(e)

    def digit_count(self, row):
        """Count the number of digits in a row"""
        return len(row)

    def settingup_failed_reiteration(self, exported_nopol_col_id):
        """Set up data for re-iteration based on failed data"""
        failed_data = pd.read_excel(self.filename, sheet_name=self.error_sheetname)
        failed_data.drop_duplicates(inplace=True, subset="plate")
        failed_data.dropna(inplace=True, how='all', axis=0)
        failed_data.reset_index(inplace=True, drop=True)
        failed_data['plate'] = failed_data['plate'].str.strip()
        failed_data[['Kode Depan', 'Kode Tengah', 'Kode Belakang']] = failed_data['plate'].str.split(" ", expand=True)
        exported_nopol_col_name = self.df_postwebscrape.columns[exported_nopol_col_id]
        failed_data = failed_data[~failed_data['plate'].isin(self.df_postwebscrape[exported_nopol_col_name])]
        failed_data['Kode Tengah'].astype(int)
        failed_data['Digit Kode Tengah'] = failed_data['Kode Tengah'].apply(self.digit_count)
        failed_data = failed_data[failed_data['Digit Kode Tengah'] == 4]
        failed_data.reset_index(drop=True, inplace=True)
        return failed_data
    
    def failed_iteration(self, exported_nopol_col_id, step=1):
        """Perform re-iteration for the data that failed scraping"""
        failed_data = self.settingup_failed_reiteration(exported_nopol_col_id)
        print(f"Failed data has {failed_data.shape[0]} entry(ies)")
        self.df_failedwebscrape = self.df_failedwebscrape.drop(self.df_failedwebscrape.index)
        self.webscraping(df=failed_data,
                         nopol_col_id=0,
                         kodedepan_col_id=2,
                         kodetengah_col_id=3,
                         kodebelakang_col_id=4,
                         step=step)
        
    def finishing_data(self, exported_nopol_col_id, final_filename, final_sheetname):
        """Finalize data by removing duplicates and saving it in the final file"""
        df_raw = pd.read_excel(self.filename, sheet_name=self.main_sheetname)
        exported_nopol_col_raw = df_raw.columns[exported_nopol_col_id]
        self.df_final = df_raw.drop_duplicates(subset=exported_nopol_col_raw)
        self.df_final.reset_index(drop=True, inplace=True)
        self.df_final.to_excel(final_filename, sheet_name=final_sheetname, index=False)
        print(f"Final Data is saved in {final_filename}!")
        return self.df_final
