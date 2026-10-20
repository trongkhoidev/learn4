import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const screenshotDir = path.resolve(process.cwd(), '../docs/verification/screenshots');

test('capture current desktop and mobile flows for the handoff report', async ({ page }) => {
  test.skip(!process.env.CAPTURE_REFACTOR_SCREENSHOTS, 'Run only when handoff screenshots are requested.');
  fs.mkdirSync(screenshotDir, { recursive: true });
  await page.setViewportSize({ width: 1440, height: 1000 });

  await page.goto('/teacher');
  await page.getByPlaceholder('Nhập mã giáo viên').fill('playwright-teacher-code');
  await page.getByRole('button', { name: 'Vào hệ thống' }).click();
  await expect(page.getByRole('heading', { name: 'Trung tâm tuần này' })).toBeVisible();
  await page.getByRole('button', { name: 'Tạo lớp học', exact: true }).first().click();
  const className = 'Screenshot B1 Class';
  await page.getByPlaceholder('Ví dụ: IELTS Foundation 03').fill(className);
  await page.getByPlaceholder('A2, B1, IELTS 5.5, Tiếng Anh thiếu nhi').fill('B1');
  await page.getByRole('button', { name: 'Tạo lớp', exact: true }).click();
  await expect(page.getByRole('link', { name: className, exact: true })).toBeVisible();
  await page.waitForTimeout(700);
  await page.screenshot({ path: path.join(screenshotDir, 'teacher-dashboard-desktop.png'), fullPage: true });

  const classList = await page.evaluate(async () => {
    const response = await fetch('/api/v1/classes', { headers: { 'X-Teacher-Code': 'playwright-teacher-code' } });
    return response.json();
  });
  const createdClass = classList.find(item => item.name === className);
  expect(createdClass).toBeTruthy();
  await page.goto(`/join?code=${createdClass.share_code}`);
  await expect(page.getByText(className, { exact: true })).toBeVisible();
  await page.getByPlaceholder('Nhập họ và tên...').fill('Screenshot Learner');
  await page.getByRole('button', { name: 'Vào lớp' }).click();
  await expect(page.getByRole('heading', { name: /Xin chào, Screenshot Learner!/ })).toBeVisible();
  await page.waitForTimeout(700);
  await page.screenshot({ path: path.join(screenshotDir, 'student-home-desktop.png'), fullPage: true });

  await page.goto('/speaking/practice');
  await expect(page.getByRole('heading', { name: 'Chọn chủ đề để bắt đầu' })).toBeVisible();
  await page.locator('h3.font-bold').first().click();
  await expect(page.getByRole('button', { name: 'Bắt đầu 1 phút chuẩn bị' })).toBeVisible();
  await page.screenshot({ path: path.join(screenshotDir, 'speaking-practice-desktop.png'), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(screenshotDir, 'speaking-practice-mobile.png'), fullPage: true });
});
