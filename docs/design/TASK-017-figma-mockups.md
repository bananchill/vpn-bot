# TASK-017: Figma Mockup Specifications

**Figma File:** `3w35CgIrnyNqPaC9I89jul`
**Reference Nodes:** 12:2 (Settings), 13:2 (Dashboard), 14:2 (Users), 15:2 (User Detail)
**Target:** 375px mobile width, iOS-style Telegram WebApp

---

## Design System Reference (extracted from existing pages)

### Colors
| Token | Value |
|---|---|
| Background | `#f5f5f7` |
| Card surface | `#ffffff` |
| Text primary | `#1a1a2e` |
| Text secondary / hint | `#8e8e93` |
| Text body | `#3c3c43` |
| Accent / link | `#007aff` |
| Border / divider | `rgba(0,0,0,0.06)` (6% black) |
| Header border | `rgba(0,0,0,0.08)` |
| Card shadow | `0 1px 3px rgba(0,0,0,0.04)` |
| Chip shadow | `0 1px 2px rgba(0,0,0,0.04)` |
| Success bg | `#e8f5e9` |
| Success text | `#2e7d32` |
| Success icon | `#4caf50` |
| Error bg | `#fce4ec` |
| Error text | `#c62828` |
| Warning bg | `#fff3e0` |
| Warning text | `#e65100` |
| Info bg | `#e3f2fd` |
| Info text | `#1565c0` |
| Purple bg | `#f3e5f5` |
| Toggle on | `#34c759` |
| Surface tertiary | `#f5f5f7` |
| Chevron / inactive | `#c7c7cc` |

### Typography (Inter font)
| Style | Size / Weight |
|---|---|
| Page title (header) | 17px / semibold (600) |
| Section heading | 18px / semibold |
| Large name | 20px / bold (700) |
| Hero number | 24px / bold |
| Greeting | 26px / bold |
| Card title | 15px / semibold |
| Body text | 14px / medium (500) |
| Body regular | 15px / regular |
| Small label | 13px / medium |
| Tiny label | 12px / regular |
| Section label (uppercase) | 13px / semibold, uppercase, letter-spacing 0.5px |
| Stat sublabel | 11px / regular |
| Tab label | 10px / regular |

### Spacing
| Element | Value |
|---|---|
| Page padding | 16px horizontal, 20px vertical |
| Card padding | 16px |
| Card border-radius | 16px |
| Button border-radius | 14px |
| Chip border-radius | 20px |
| Avatar small radius | 14px |
| Avatar large radius | 22px |
| Icon container radius | 10px |
| Grid gap | 12px |
| List item gap | 10px |
| Section spacing | 20px (space-y-5) |

### Layout
| Element | Height |
|---|---|
| Header (main pages) | 49px |
| Header (sub-pages with back) | 58px |
| Bottom navbar | 81px |
| Primary button | 52px |
| Small button | 32px |
| Search input | 41px |
| User card | 72px |
| Chip | 29px |
| Icon container (stat) | 36x36px |
| Icon container (action) | 40x40px |
| Avatar small | 44x44px |
| Avatar large | 72x72px |
| Pagination button | 36x36px |

---

## Page 1: LogsView (node target: 16:2)

**Route:** `/logs`
**Header:** "Логи" with back arrow (58px height)
**Frame:** 375 x 812px, background `#f5f5f7`

### Layout (top to bottom, px-4 py-5 space-y-4)

#### 1.1 Filter Dropdown Row

A horizontally scrollable row of filter chips (same pattern as UsersListView filter chips).

**Container:** `flex gap-2 overflow-x-auto`, horizontal scroll, no scrollbar, full bleed with `-mx-4 px-4`

**Chips:**
- "Все действия" (default active)
- "Блокировка"
- "Подписка"
- "Настройки"
- "Промокоды"
- "Конфиги"

**Active chip style:**
- Background: `#007aff`
- Text: `#ffffff`
- Height: 29px
- Padding: 7px 14px
- Font: 13px medium
- Border-radius: 20px

**Inactive chip style:**
- Background: `#ffffff`
- Text: `#8e8e93`
- Shadow: `0 1px 2px rgba(0,0,0,0.04)`
- Same dimensions as active

#### 1.2 Count Text

- Text: "Найдено: 347 записей"
- Font: 13px regular
- Color: `#8e8e93`

#### 1.3 Log Entries Card

A single white card containing all log rows with dividers between them.

**Card:**
- Background: `#ffffff`
- Border-radius: 16px
- Shadow: `0 1px 3px rgba(0,0,0,0.04)`
- Overflow: hidden
- No internal padding (rows handle their own)

**Each Row:** `flex items-center gap-3 px-4 py-3`
- Divider between rows: `border-b border-black/[0.06]` (not on last row)

**Row content:**

**Left: Action Icon (36x36px, rounded-10px)**

Icon backgrounds by action type:
| Action | Emoji | Background |
|---|---|---|
| block_user | (red circle) | `#fce4ec` |
| unblock_user | (green check) | `#e8f5e9` |
| extend_subscription | (clock) | `#e3f2fd` |
| update_note | (pencil) | `#f3e5f5` |
| toggle_config | (key) | `#fff3e0` |
| update_settings | (gear) | `#f5f5f7` |
| create_promo | (tag) | `#e3f2fd` |
| toggle_promo | (tag) | `#fff3e0` |
| delete_promo | (trash) | `#fce4ec` |

**Center: Text block (flex-1 min-w-0)**
- Line 1: Action description text
  - Font: 14px medium
  - Color: `#1a1a2e`
  - Truncate if too long
  - Example: "Заблокирован @ivan"
- Line 2: Admin who did it + timestamp
  - Font: 12px regular
  - Color: `#8e8e93`
  - Example: "@admin_user -- 15:42"

**Show 20 rows per page.**

Sample rows for mockup:
1. block_user: "Заблокирован @ivan" / "@admin -- 15:42"
2. extend_subscription: "Подписка продлена @maria (+30 дн)" / "@admin -- 14:20"
3. create_promo: "Создан промокод SUMMER25" / "@admin -- 11:05"
4. update_settings: "Настройки обновлены" / "@admin -- 10:30"
5. toggle_config: "Конфиг отключён @user123" / "@admin -- 09:15"

#### 1.4 Pagination

Same component as UsersListView pagination:
- Centered row of 36x36px buttons
- Active page: bg `#007aff`, text `#ffffff`
- Inactive: bg `#ffffff`, text `#8e8e93`, shadow
- Border-radius: 10px
- Gap: 4px
- Show: 1 ... 3 [4] 5 ... 18

---

## Page 2: PromosListView (node target: 17:2)

**Route:** `/promos`
**Header:** "Промокоды" (49px height, no back button -- this is a main tab page)
**Frame:** 375 x 812px, background `#f5f5f7`

### Layout (top to bottom, px-4 py-5 space-y-4)

#### 2.1 Top Action Row

**Layout:** `flex items-center justify-between`

**Left: Count text**
- Text: "3 промокода"
- Font: 13px regular
- Color: `#8e8e93`

**Right: Add button**
- Text: "+ Создать"
- Font: 13px medium
- Color: `#007aff`
- Background: transparent (just text button)
- Active: opacity 0.7

#### 2.2 Promo Cards List

Each promo code is a separate white card. Gap between cards: 10px.

**Card structure:**
- Background: `#ffffff`
- Border-radius: 16px
- Shadow: `0 1px 3px rgba(0,0,0,0.04)`
- Padding: 16px

**Card content (vertical stack, gap-3):**

**Top row:** `flex items-center justify-between`
- Left: Code text
  - Font: 17px bold
  - Color: `#1a1a2e`
  - Example: "SUMMER25"
- Right: Discount badge
  - Text: "-25%"
  - Font: 13px semibold
  - Background: `#e8f5e9`
  - Color: `#2e7d32`
  - Padding: 2px 8px
  - Border-radius: 6px

**Progress section:**
- Label row: `flex justify-between`
  - Left: "Использований"
    - Font: 12px regular
    - Color: `#8e8e93`
  - Right: "12/100"
    - Font: 12px medium
    - Color: `#1a1a2e`
- Progress bar (below label, mt-1):
  - Track: `#f5f5f7`, height 6px, border-radius 3px, full width
  - Fill: `#007aff`, width proportional (12%), border-radius 3px
  - If >80% fill: use `#e65100` (warning orange)
  - If 100%: use `#c62828` (error red)

**Bottom row:** `flex items-center justify-between`
- Left: Status badge
  - Active: bg `#e8f5e9`, text `#2e7d32`, label "Активен"
  - Inactive: bg `#fce4ec`, text `#c62828`, label "Неактивен"
  - Expired: bg `#fff3e0`, text `#e65100`, label "Истёк"
  - Font: 11px semibold
  - Padding: 2px 8px
  - Border-radius: 6px
- Right: Expiry date
  - Text: "до 04.04.2026"
  - Font: 12px regular
  - Color: `#8e8e93`

**Entire card is tappable** (navigates to PromoDetailView). Right chevron optional.

#### 2.3 Sample Mockup Data

Card 1:
- Code: "SUMMER25", Discount: -25%, Usage: 12/100, Status: Active, Expiry: 04.04.2026

Card 2:
- Code: "WELCOME10", Discount: -10%, Usage: 45/50, Status: Active, Expiry: 15.03.2026

Card 3:
- Code: "VIP50", Discount: -50%, Usage: 5/5, Status: Inactive, Expiry: 01.03.2026

#### 2.4 Empty State

When no promos exist, show the standard EmptyState component:
- Icon: box SVG (same as UsersListView)
- Message: "Нет промокодов"
- Description: "Создайте первый промокод для ваших пользователей"
- Action button: "Создать промокод" (btn-primary)

---

## Page 3: PromoCreateView (node target: 18:2)

**Route:** `/promos/create`
**Header:** "Новый промокод" with back arrow (58px height)
**Frame:** 375 x 812px, background `#f5f5f7`

### Layout (top to bottom, px-4 py-5 space-y-5)

Uses the iOS grouped form style from SettingsView.

#### 3.1 Section: "КОД ПРОМОКОДА"

**Section label:**
- Text: "КОД ПРОМОКОДА"
- Font: 13px semibold, uppercase, letter-spacing 0.5px
- Color: `#8e8e93`
- Margin bottom: 8px
- Padding left: 4px

**Grouped card:**
- Background: `#ffffff`
- Border-radius: 16px
- Shadow: `0 1px 3px rgba(0,0,0,0.04)`
- Overflow: hidden

**Single row with input + generate button:**
- Layout: `flex items-center px-4 py-3 gap-2`
- Left: Input field
  - Flex: 1
  - Font: 15px regular
  - Color: `#1a1a2e`
  - Placeholder: "Введите код" in `#c7c7cc`
  - Background: transparent
  - No border
  - Value shown: "SUMMER25"
- Right: Generate button
  - Text: "Создать" (or dice emoji + "Создать")
  - Font: 13px medium
  - Color: `#007aff`
  - Background: `#f5f5f7`
  - Border-radius: 10px
  - Height: 32px
  - Padding: 8px 14px

#### 3.2 Section: "ПАРАМЕТРЫ"

**Section label:** Same style as above, text "ПАРАМЕТРЫ"

**Grouped card:** (3 rows with dividers)

**Row 1: Discount percent**
- Layout: `px-4 pt-3 pb-px border-b border-black/[0.06]`
- Label: "Скидка (%)" -- 12px, `#8e8e93`
- Input: number, 15px, `#1a1a2e`, placeholder "25"
- Full width, transparent bg

**Row 2: Max activations**
- Layout: `px-4 pt-3 pb-px border-b border-black/[0.06]`
- Label: "Макс. активаций" -- 12px, `#8e8e93`
- Input: number, 15px, `#1a1a2e`, placeholder "100"

**Row 3: (last row, no bottom border)**
- Layout: `px-4 pt-3 pb-3`
- This is a display-only row or can be omitted; validity is handled in the next section

#### 3.3 Section: "СРОК ДЕЙСТВИЯ"

**Section label:** Same style, text "СРОК ДЕЙСТВИЯ"

**Preset chips row:**
- Layout: `flex gap-2 mb-3`
- Chips: "7 дн", "14 дн", "30 дн", "90 дн"
- Active chip (e.g., "30 дн"):
  - Background: `#007aff`
  - Text: `#ffffff`
- Inactive chips:
  - Background: `#ffffff`
  - Text: `#8e8e93`
  - Shadow: `0 1px 2px rgba(0,0,0,0.04)`
- Same chip dimensions as filter chips: 29px height, 20px radius, 13px medium

**Custom date input (below chips):**
- Grouped card with single row:
  - Label: "Или точная дата" -- 12px, `#8e8e93`
  - Input: date picker, 15px, `#1a1a2e`, placeholder "дд.мм.гггг"
  - Note: when a preset chip is selected, this field shows the calculated date (grayed out)

#### 3.4 Create Button

- Full width
- Text: "Создать промокод"
- Font: 16px semibold
- Color: `#ffffff`
- Background: `#007aff`
- Border-radius: 14px
- Height: 52px
- Disabled state: opacity 50%

#### 3.5 Spacing Notes

- The form should have enough space above the bottom navbar (81px) for comfortable scrolling
- Add `pb-[100px]` to ensure the create button is not hidden behind navbar

---

## Page 4: PromoDetailView (node target: 19:2)

**Route:** `/promos/:id`
**Header:** "Промокод" with back arrow (58px height)
**Frame:** 375 x 812px, background `#f5f5f7`

### Layout (top to bottom, px-4 py-5 space-y-4)

#### 4.1 Top Card: Code Overview

Similar to UserInfo card in UserDetailView.

**Card:**
- Background: `#ffffff`
- Border-radius: 20px (same as UserInfo)
- Shadow: `0 1px 3px rgba(0,0,0,0.04)`
- Overflow: hidden

**Content (centered, px-4 pt-5 pb-0):**

**Code display:**
- Text: "SUMMER25"
- Font: 24px bold
- Color: `#1a1a2e`
- Centered

**Discount badge (below code, mt-2):**
- Text: "-25%"
- Font: 14px semibold
- Background: `#e8f5e9`
- Color: `#2e7d32`
- Padding: 4px 12px
- Border-radius: 8px
- Centered

**Status badges row (mt-2):**
- Same as UserInfo badges row
- Show: "Активен" badge (green) or "Неактивен" (red)

**Progress section (mt-4, px-4):**
- Full-width progress bar:
  - Label above: "Использований" left, "12 / 100" right
  - Font: 13px, colors: label `#8e8e93`, value `#1a1a2e`
  - Track: `#f5f5f7`, 6px, radius 3px
  - Fill: `#007aff`, 12%

**Stats row (same pattern as UserInfo stats):**
- Border-top: `border-black/[0.06]`
- Padding: 17px top, 16px bottom, 18px horizontal
- Margin top: 16px
- Three columns centered:
  - Column 1: "12" / "Активаций" (18px bold / 11px `#8e8e93`)
  - Column 2: "25%" / "Скидка" (18px bold / 11px `#8e8e93`)
  - Column 3: "04.04" / "Истекает" (18px bold / 11px `#8e8e93`)

#### 4.2 Info Rows Card

**Card:**
- Background: `#ffffff`
- Border-radius: 16px
- Shadow: `0 1px 3px rgba(0,0,0,0.04)`
- Overflow: hidden

**Rows** (each: `flex justify-between items-center px-4 py-3`, divider between):

| Left label (14px, `#8e8e93`) | Right value (14px medium, `#1a1a2e`) |
|---|---|
| Статус | Активен (green text `#2e7d32`) |
| Создан | 05.03.2026 |
| Действует до | 04.04.2026 |
| Код | SUMMER25 |

#### 4.3 Usage History Section

**Section heading:**
- Text: "История применений"
- Font: 18px semibold
- Color: `#1a1a2e`
- Margin bottom: 12px

**Usage list card:**
- Background: `#ffffff`
- Border-radius: 16px
- Shadow: `0 1px 3px rgba(0,0,0,0.04)`
- Overflow: hidden

**Each usage row:** `flex items-center gap-3 px-4 py-3`
- Divider between rows: `border-b border-black/[0.06]` (not on last)

**Row content:**
- Left: Avatar (36x36px, rounded-10px)
  - Gradient background (same gradient array as UserCard)
  - White initial letter, 14px semibold
- Center: User info (flex-1 min-w-0)
  - Line 1: "@ivan" -- 14px medium, `#1a1a2e`
  - Line 2: "04.03.2026 14:23" -- 12px, `#8e8e93`
- Right: No chevron needed

**Sample usage data:**
1. @ivan -- 04.03.2026 14:23
2. @maria -- 03.03.2026 09:11
3. @sergey -- 02.03.2026 18:45
4. @anna -- 01.03.2026 12:30
5. @dmitry -- 28.02.2026 16:20

If more than 10 usages, show pagination below the card.

If no usages: show inline empty text:
- "Промокод ещё не использован"
- Font: 14px regular
- Color: `#8e8e93`
- Centered in card, py-6

#### 4.4 Action Buttons

**Layout:** `space-y-2 pt-2` (same as UserDetailView)

**Deactivate button:**
- Full width
- Height: 47px
- Border-radius: 14px
- Font: 15px semibold
- Background: `#fff3e0`
- Color: `#e65100`
- Text: "Деактивировать"
- When promo is already inactive, text changes to "Активировать" with:
  - Background: `#007aff`
  - Color: `#ffffff`

**Delete button:**
- Full width
- Height: 47px
- Border-radius: 14px
- Font: 15px semibold
- Background: `#fce4ec`
- Color: `#c62828`
- Text: "Удалить промокод"

**Spacing note:** Add `pb-[100px]` for navbar clearance.

---

## Figma Frame Structure

Create these frames in the Figma file under a new page or section:

```
TASK-017 Designs/
  LogsView           375x812   node 16:2
  PromosListView     375x812   node 17:2
  PromoCreateView    375x812   node 18:2
  PromoDetailView    375x812   node 19:2
```

Each frame should include:
- The sticky header at the top
- Content area with `#f5f5f7` background
- The bottom navbar at the bottom (4 tabs: Home, Users, Promo, More)
- For LogsView: "More" tab active
- For Promos pages: "Promo" tab active

### Reusable Components to Create

Before building the pages, create these new components (or instances):

1. **LogEntryRow** -- icon + text + timestamp
2. **PromoCard** -- code + discount + progress bar + status + expiry
3. **ProgressBar** -- track + fill, configurable width percentage
4. **FilterChip** -- reuse from UsersListView pattern
5. **UsageRow** -- avatar + username + date (similar to LogEntryRow)
6. **FormGroupedCard** -- reuse pattern from SettingsForm
7. **PresetChip** -- validity period selector chip

### Notes for Implementation Handoff

All new components follow existing patterns:
- Cards are always white, rounded-16px, shadow `0 1px 3px rgba(0,0,0,0.04)`
- List items inside cards use `px-4 py-3` with `border-b border-black/[0.06]` dividers
- Icons are 36x36px with rounded-10px and colored backgrounds
- Filter chips are 29px height, rounded-20px, 13px medium
- Action buttons are 47px or 52px height, rounded-14px, 15-16px semibold
- Text uses `#1a1a2e` primary, `#8e8e93` secondary, `#007aff` accent
- All spacing follows 4px grid (4, 8, 12, 16, 20, 24, 32, 40, 48, 64)
