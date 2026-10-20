import { test, expect } from '@playwright/test';

test.describe('Speaking Module', () => {
  async function enterSpeaking(page) {
    await page.goto('/speaking');
    const nameInput = page.getByLabel('Tên học viên');
    const dashboard = page.getByRole('heading', { name: /Chào .+, mình cùng luyện nói nhé\./ });
    await Promise.race([
      nameInput.waitFor({ state: 'visible' }),
      dashboard.waitFor({ state: 'visible' }),
    ]);
    if (await nameInput.isVisible()) {
      await nameInput.fill('Playwright Tester');
      await page.getByRole('button', { name: 'Vào khu vực luyện nói' }).click();
    }
    await expect(dashboard).toBeVisible();
  }

  test('Teacher access, class creation, student join, and deep-link refresh', async ({ page }) => {
    const rejected = await page.request.get('/api/v1/classes', {
      headers: { 'X-Teacher-Code': 'incorrect-code' },
    });
    expect(rejected.status()).toBe(403);

    await page.goto('/teacher');
    await page.getByPlaceholder('Nhập mã giáo viên').fill('playwright-teacher-code');
    await page.getByRole('button', { name: 'Vào hệ thống' }).click();
    await expect(page.getByRole('heading', { name: 'Trung tâm tuần này' })).toBeVisible();
    await page.getByRole('button', { name: 'Tạo lớp học', exact: true }).first().click();

    const className = 'Playwright B1 Class';
    await page.getByPlaceholder('Ví dụ: IELTS Foundation 03').fill(className);
    await page.getByPlaceholder('A2, B1, IELTS 5.5, Tiếng Anh thiếu nhi').fill('B1');
    await page.getByRole('button', { name: 'Tạo lớp', exact: true }).click();
    await expect(page.getByRole('link', { name: className, exact: true })).toBeVisible();

    const classesResponse = await page.request.get('/api/v1/classes', {
      headers: { 'X-Teacher-Code': 'playwright-teacher-code' },
    });
    const classes = await classesResponse.json();
    const createdClass = classes.find(item => item.name === className);
    expect(createdClass).toBeTruthy();
    await page.getByRole('link', { name: className, exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`/teacher/class/${createdClass.id}$`));
    await expect(page.getByRole('heading', { name: className })).toBeVisible();

    await page.goto(`/join?code=${createdClass.share_code}`);
    await expect(page.getByText(className, { exact: true })).toBeVisible();
    await page.getByPlaceholder('Nhập họ và tên...').fill('Playwright Learner');
    await page.getByRole('button', { name: 'Vào lớp' }).click();
    await expect(page).toHaveURL(new RegExp(`/student/${createdClass.id}$`));
    await expect(page.getByRole('heading', { name: /Xin chào, Playwright Learner!/ })).toBeVisible();
    await expect(page.getByText(className).first()).toBeVisible();
    await expect.poll(() => page.evaluate(id => localStorage.getItem(`student_name_${id}`), createdClass.id))
      .toBe('Playwright Learner');

    await page.reload();
    await expect(page.getByRole('heading', { name: /Xin chào, Playwright Learner!/ })).toBeVisible();
  });

  test('Dashboard and Practice navigation', async ({ page }) => {
    // 1. Visit Dashboard
    await enterSpeaking(page);
    
    // Verify Dashboard rendered
    await expect(page.getByRole('heading', { name: /Chào Playwright Tester, mình cùng luyện nói nhé\./ })).toBeVisible();
    
    // 2. Click Practice
    await page.getByRole('link', { name: 'Luyện theo chủ đề', exact: true }).click();
    
    // Verify Practice page rendered
    await expect(page.getByRole('heading', { name: 'Chọn chủ đề để bắt đầu' })).toBeVisible();
    
    // Wait for topics to load
    await page.waitForSelector('h3.font-bold');
    
    // 3. Click first topic
    await page.locator('h3.font-bold').first().click();
    
    // Verify Part selection rendered
    await expect(page.getByRole('tab', { name: 'PART 2' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'PART 1' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Bắt đầu 1 phút chuẩn bị' })).toBeVisible();
    
    // 4. Click Part 1
    await page.getByRole('tab', { name: 'PART 1' }).click();
    await expect(page.getByRole('tab', { name: 'PART 1' })).toHaveAttribute('aria-selected', 'true');
    
    // Go back to dashboard via header link
    await page.locator('a', { hasText: 'Quay lại Dashboard' }).click();
    await expect(page.getByRole('heading', { name: /Chào Playwright Tester, mình cùng luyện nói nhé\./ })).toBeVisible();
  });

  test('Part 2 preparation counts down for one minute before enabling recording', async ({ page }) => {
    await page.clock.install();
    await enterSpeaking(page);
    await page.getByRole('link', { name: 'Luyện theo chủ đề', exact: true }).click();
    await page.waitForSelector('h3.font-bold');
    await page.locator('h3.font-bold').first().click();
    await expect(page.getByRole('button', { name: 'Bắt đầu 1 phút chuẩn bị' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Bắt đầu ghi âm' })).toHaveCount(0);

    await page.getByRole('button', { name: 'Bắt đầu 1 phút chuẩn bị' }).click();
    await page.clock.runFor(1000);
    await expect(page.getByText('00:59', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Bắt đầu ghi âm' })).toHaveCount(0);

    await page.clock.fastForward(29000);
    await expect(page.getByText('00:30', { exact: true })).toBeVisible();

    await page.clock.fastForward(30000);
    await expect(page.getByText('00:00', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Bắt đầu ghi âm' })).toBeVisible();
  });
  
  test('Mock Test navigation', async ({ page }) => {
    // 1. Visit Dashboard
    await enterSpeaking(page);
    
    // 2. Click Mock Test
    await page.getByRole('link', { name: 'Thi thử', exact: true }).click();
    
    // Wait for questions to load
    await expect(page.getByRole('heading', { name: /Mock Test/ })).toBeVisible({ timeout: 15000 });
  });
  
  test('History navigation', async ({ page }) => {
    await enterSpeaking(page);
    
    await page.getByRole('link', { name: 'Lịch sử', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Lịch sử & Tiến độ' })).toBeVisible();
  });

  test('Completed three-Part mock displays persisted examiner feedback', async ({ page }) => {
    await page.clock.install();
    await enterSpeaking(page);
    const topics = await (await page.request.get('/api/v1/speaking/topics')).json();
    const topic = topics[0];
    const questions = [1, 2, 3].map(part => topic.questions.find(question => question.part === part));
    expect(questions.every(Boolean)).toBeTruthy();
    await page.route('**/api/v1/speaking/questions?*', route => route.fulfill({ json: questions }));
    await page.getByRole('link', { name: 'Thi thử', exact: true }).click();

    for (const question of questions) {
      await expect(page.getByRole('heading', { name: question.question_text, exact: true })).toBeVisible();
      if (question.part === 2) {
        await page.getByRole('button', { name: 'Bắt đầu 1 phút chuẩn bị' }).click();
        await page.clock.fastForward(60000);
      }
      await page.getByRole('button', { name: 'Bắt đầu ghi âm' }).click();
      await page.waitForTimeout(1200);
      await page.getByRole('button', { name: 'Dừng ghi âm' }).click();
      await page.getByRole('button', { name: 'Nộp bản ghi âm' }).click();
    }

    await expect(page.getByRole('heading', { name: 'Hoàn Thành Mock Test' })).toBeVisible({ timeout: 15000 });
    const feedback = page.getByRole('region', { name: 'Phản hồi theo tiêu chí' });
    await expect(feedback.getByRole('heading')).toHaveCount(4);
    await expect(feedback.getByText('Vì sao có band này?', { exact: true })).toHaveCount(3);
    await expect(feedback.locator('blockquote')).toHaveCount(3);
    await expect(page.getByRole('heading', { name: 'Không có lỗi được xác nhận' })).toBeVisible();
  });

  test('Fake microphone records, submits, shows a partial result, and appears in history', async ({ page }) => {
    await page.addInitScript(() => {
      const speechSynthesis = window.speechSynthesis;
      const cancel = speechSynthesis.cancel.bind(speechSynthesis);
      window.__speechCancelCount = 0;
      speechSynthesis.cancel = () => {
        window.__speechCancelCount += 1;
        cancel();
      };
    });
    await enterSpeaking(page);
    await page.getByRole('link', { name: 'Luyện theo chủ đề', exact: true }).click();
    await page.waitForSelector('h3.font-bold');
    await page.locator('h3.font-bold').first().click();
    await page.getByRole('tab', { name: 'PART 1' }).click();
    const cancelCountBeforeRecording = await page.evaluate(() => window.__speechCancelCount);
    await page.getByRole('button', { name: 'Bắt đầu ghi âm' }).click();
    await expect.poll(() => page.evaluate(() => window.__speechCancelCount)).toBeGreaterThan(cancelCountBeforeRecording);
    await expect(page.getByText('Đang ghi âm...')).toBeVisible();
    await page.waitForTimeout(1200);
    await page.getByRole('button', { name: 'Dừng ghi âm' }).click();
    await expect(page.getByText('Đã ghi âm xong')).toBeVisible();
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: 'Nghe lại bản ghi' }).click();
    await expect(page.getByRole('button', { name: 'Tạm dừng nghe lại' })).toBeVisible();
    await page.getByRole('button', { name: 'Tạm dừng nghe lại' }).click();

    const pendingResponse = page.waitForResponse(response =>
      response.url().includes('/api/v1/speaking/practice')
      && response.request().method() === 'POST'
    );
    await page.getByRole('button', { name: 'Nộp bản ghi âm' }).click();
    const submitted = await pendingResponse;
    expect(submitted.ok()).toBeTruthy();
    const submittedSession = await submitted.json();
    expect(submittedSession.status).toBe('pending');
    expect(submittedSession.audio_url).toMatch(/^\/storage\//);
    const storedAudio = await page.request.get(submittedSession.audio_url);
    expect(storedAudio.ok()).toBeTruthy();
    await expect(page.getByRole('heading', { name: 'Kết Quả Phân Tích' })).toBeVisible({ timeout: 15000 });
    const persistedResult = await (await page.request.get(`/api/v1/speaking/practice/${submittedSession.id}`)).json();
    expect(persistedResult.result.overall).toBeNull();
    await expect(page.getByText('Điểm ngôn ngữ tham khảo', { exact: true })).toBeVisible();
    await expect(page.getByText('Trung bình 3 tiêu chí ngôn ngữ. Chưa phải band tổng thể vì còn thiếu đánh giá Phát âm.')).toBeVisible();
    const feedback = page.getByRole('region', { name: 'Phản hồi theo tiêu chí' });
    await expect(feedback.getByRole('heading', { name: 'Pronunciation', exact: true })).toBeVisible();
    await expect(feedback.getByText('Bước luyện tiếp theo', { exact: true })).toHaveCount(4);
    await expect(feedback.getByText('Vì sao có band này?', { exact: true })).toHaveCount(3);
    await expect(feedback.getByText('Để tiến tới band cao hơn', { exact: true })).toHaveCount(3);
    await expect(feedback.locator('blockquote')).toHaveCount(3);
    await expect(page.getByRole('button', { name: 'Bắt đầu ghi âm' })).toHaveCount(0);

    await page.getByRole('button', { name: 'Luyện chủ đề khác' }).click();
    await page.getByRole('link', { name: 'Quay lại Dashboard' }).click();
    await page.getByRole('link', { name: 'Lịch sử', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Lịch sử & Tiến độ' })).toBeVisible();
    const partialRow = page.getByTestId('speaking-history-row').filter({ hasText: 'Một phần' }).last();
    await expect(partialRow).toContainText('Phần thi: PART 1');
    await partialRow.getByRole('link', { name: 'Xem phản hồi' }).click();
    await expect(page.getByRole('heading', { name: 'Kết Quả Phân Tích' })).toBeVisible();
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Kết Quả Phân Tích' })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Phản hồi theo tiêu chí' }).getByRole('heading')).toHaveCount(4);
    await expect(page.getByText('Vì sao có band này?', { exact: true })).toHaveCount(3);
  });

  test('Failed result remains bandless and visible in history', async ({ page }) => {
    let polls = 0;
    const failure = {
      schema_version: 'speaking-v3', scope: 'practice_answer', status: 'failed',
      transcript: '', overall: null, noise: null, is_relevant: null,
      pronun: { status: 'failed', band: null, score: null, reason: 'No validated pronunciation method.' },
      fluency: { status: 'failed', band: null, score: null, feedback: 'Nhà cung cấp chấm chưa sẵn sàng.' },
      grammar: { status: 'failed', band: null, score: null },
      vocab: { status: 'failed', band: null, score: null },
      color_coded_transcript: [], uncertain_spans: [], review_reasons: ['llm_provider_not_ready'],
    };
    await page.route('**/api/v1/speaking/practice', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({ json: {
          id: 'failed-session', student_name: 'Playwright Tester', status: 'pending',
          result: { status: 'pending' }, created_at: new Date().toISOString(),
        } });
        return;
      }
      await route.continue();
    });
    await page.route('**/api/v1/speaking/practice/failed-session', async route => {
      polls += 1;
      if (polls < 2) {
        await route.fulfill({ json: {
          id: 'failed-session', student_name: 'Playwright Tester', status: 'pending',
          result: { status: 'pending' }, created_at: new Date().toISOString(),
        } });
      } else {
        await route.fulfill({ json: {
          id: 'failed-session', student_name: 'Playwright Tester', status: 'failed',
          result: failure, score: null, part_type: 'PART 1', created_at: new Date().toISOString(),
        } });
      }
    });
    await page.route('**/api/v1/speaking/history?*', route => route.fulfill({ json: [{
      id: 'failed-session', student_name: 'Playwright Tester', status: 'failed',
      result: failure, score: null, part_type: 'PART 1', created_at: new Date().toISOString(),
    }] }));
    await page.route('**/api/v1/speaking/progress?*', route => route.fulfill({ json: { estimated_band: null, streak: 0 } }));

    await enterSpeaking(page);
    await page.getByRole('link', { name: 'Luyện theo chủ đề', exact: true }).click();
    await page.waitForSelector('h3.font-bold');
    await page.locator('h3.font-bold').first().click();
    await page.getByRole('tab', { name: 'PART 1' }).click();
    await page.getByRole('button', { name: 'Bắt đầu ghi âm' }).click();
    await page.waitForTimeout(900);
    await page.getByRole('button', { name: 'Dừng ghi âm' }).click();
    const pendingResponse = page.waitForResponse(response =>
      response.url().includes('/api/v1/speaking/practice')
      && response.request().method() === 'POST'
    );
    await page.getByRole('button', { name: 'Nộp bản ghi âm' }).click();
    expect((await pendingResponse).ok()).toBeTruthy();
    await expect(page.getByRole('heading', { name: 'Kết Quả Phân Tích' })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('llm_provider_not_ready')).toBeVisible();
    await expect(page.getByText('Chưa chấm được')).toHaveCount(4);
    await page.getByRole('button', { name: 'Luyện chủ đề khác' }).click();
    await page.getByRole('link', { name: 'Quay lại Dashboard' }).click();
    await page.getByRole('link', { name: 'Lịch sử', exact: true }).click();
    const failedRow = page.getByTestId('speaking-history-row').filter({ hasText: 'Không chấm được' }).last();
    await expect(failedRow).toContainText('—');
  });
});


test('Context board shows proposed names inline and saves learner confirmation separately', async ({ page }) => {
  const text = 'Yes, I absolutely love my hometown, Quang Tri. It has a peaceful atmosphere. Even though I am currently still in Ghana, I always look forward to visiting home.';
  const tokens = text.split(' ').map((word, index) => ({
    id: `w${index + 1}`, word, start: index * .4, end: index * .4 + .3,
    score: /Quang|still|Ghana/.test(word) ? 45 : 96,
    color: /Quang|still|Ghana/.test(word) ? 'red' : 'green',
    uncertain: /Quang|still|Ghana/.test(word),
  }));
  const idsFor = quote => {
    const source = quote.split(' ');
    const index = tokens.findIndex((word, i) => source.every((token, j) => tokens[i + j]?.word === token));
    return tokens.slice(index, index + source.length).map(word => word.id);
  };
  const suggestion = (quote, replacement, source) => ({
    quote, word_ids: idsFor(quote), replacement, source,
    kind: source === 'context_only' ? 'possible_mishearing' : 'proper_name',
    status: 'pending', confirmed_text: null,
    reason_vi: 'Cách ghi này cần được đối chiếu với bản ghi trước khi xác nhận.',
  });
  const criterion = {
    status: 'scored', band: 6, errors: [], feedback: 'Mẫu giao diện, không phải kết quả chấm audio.',
    next_action_vi: 'Nói lại một câu với lý do và ví dụ.',
    examiner_review: {
      band_reason_vi: 'Bạn phát triển ý rõ nhưng cần thêm bằng chứng về sự linh hoạt.',
      next_band_gap_vi: 'Mở rộng lý do bằng một trải nghiệm cụ thể.',
      observations: [{ kind: 'strength', quote: 'peaceful atmosphere.', word_ids: idsFor('peaceful atmosphere.'), explanation_vi: 'Cụm từ diễn tả đúng ý về quê hương.', suggestion: null }],
    },
  };
  const result = {
    schema_version: 'speaking-v3', status: 'partial', scope: 'practice_answer', overall: null,
    transcript: text, color_coded_transcript: tokens,
    fluency: criterion, vocab: criterion, grammar: criterion,
    pronun: { status: 'insufficient_evidence', feedback: 'Chưa đủ bằng chứng âm vị.', next_action_vi: 'Nghe lại một câu và ghi âm lần nữa.' },
    assessment_quality: {
      level: 'medium', coverage_score: 68, provider_count: 2, provider_agreement: 0.824,
      scope: 'language_only', timing_coverage: 1, uncertain_word_ratio: 0.24,
      language_criteria_scored: 3, pronunciation_evidence: 'missing',
      blockers_vi: ['Chưa có bằng chứng âm vị đủ tin cậy để chấm Pronunciation.'],
    },
    transcript_review: { status: 'ready', keyterms: ['Quảng Trị', 'Đà Nẵng'], suggestions: [
      suggestion('Quang Tri.', 'Quảng Trị', 'provided_term'),
      suggestion('Ghana,', 'Đà Nẵng', 'provided_term'),
    ] },
  };
  const response = { id: 'context-board', student_name: 'Playwright Tester', part_type: 'PART 1', created_at: new Date().toISOString(), result, status: 'partial' };
  await page.addInitScript(() => localStorage.setItem('speaking_name', 'Playwright Tester'));
  await page.route('**/api/v1/speaking/practice/context-board', route => route.fulfill({ json: response }));
  await page.route('**/api/v1/speaking/practice/context-board/transcript-review', async route => {
    const decision = route.request().postDataJSON();
    const item = result.transcript_review.suggestions.find(entry => entry.word_ids.join() === decision.word_ids.join());
    item.status = decision.action;
    item.confirmed_text = decision.action === 'accepted' ? decision.replacement : null;
    await route.fulfill({ json: response });
  });
  await page.goto('/speaking/practice?session=context-board');
  const quality = page.getByRole('region', { name: 'Độ phủ bằng chứng đánh giá' });
  await expect(quality).toContainText('Evidence một phần · 68/100');
  await expect(quality).toContainText('2 engine');
  await expect(quality).toContainText('82%');
  await expect(quality).toContainText('3 tiêu chí ngôn ngữ');
  const board = page.getByRole('region', { name: 'Transcript và đối chiếu' });
  await expect(board.getByRole('button', { name: 'Đối chiếu: Quang Tri. → Quảng Trị', exact: true })).toBeVisible();
  await expect(board.getByRole('button', { name: 'Đối chiếu: Ghana, → Đà Nẵng', exact: true })).toBeVisible();
  // A valid "still" stays a reviewable original, never an invented studying correction.
  await expect(board.getByRole('button', { name: 'Đối chiếu: still', exact: true })).toBeVisible();
  await expect(board.getByText('studying', { exact: true })).toHaveCount(0);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await board.screenshot({ path: '/private/tmp/learn4-transcript-board-desktop.png' });
  await board.getByRole('button', { name: 'Đối chiếu: Ghana, → Đà Nẵng', exact: true }).click();
  await expect(board.getByText('Theo tên bạn cung cấp.', { exact: false })).toBeVisible();
  await board.getByLabel('Sau khi nghe, bạn xác nhận đã nói gì?').fill('Da Nang');
  await board.getByRole('button', { name: 'Xác nhận cách ghi', exact: true }).click();
  await expect(board.getByRole('status')).toContainText('Đã lưu đối chiếu');
  expect(result.transcript).toBe(text);
  expect(result.grammar.band).toBe(6);
  await page.reload();
  await expect(board.getByRole('button', { name: 'Đối chiếu: Ghana, → Da Nang', exact: true })).toBeVisible();
  await board.getByRole('button', { name: 'Đối chiếu: Quang Tri. → Quảng Trị', exact: true }).click();
  await board.getByRole('button', { name: 'Giữ bản gốc', exact: true }).click();
  await expect(board.getByRole('button', { name: 'Đối chiếu: Quang Tri.', exact: true })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await board.screenshot({ path: '/private/tmp/learn4-transcript-board-mobile.png' });
});
