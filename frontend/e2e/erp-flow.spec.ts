import { expect, type Locator, test } from '@playwright/test'

test('admin completes an auditable order-to-inventory workflow', async ({ page }) => {
  const suffix = Date.now().toString(36).toUpperCase()
  const sku = `E2E-${suffix}`
  const productName = `E2E workflow product ${suffix}`

  await page.goto('/')
  await page.getByRole('button', { name: 'Admin' }).click()
  await page.getByRole('button', { name: /sign in/i }).click()
  await expect(page.getByText('Inventory value')).toBeVisible()

  await page.getByRole('link', { name: 'Products' }).click()
  await page.getByRole('button', { name: 'New product' }).click()
  await page.getByLabel('SKU').fill(sku)
  await page.getByLabel('Product name').fill(productName)
  await page.getByLabel('Purchase price').fill('10.00')
  await page.getByLabel('Sale price').fill('25.00')
  await page.getByLabel('Reorder threshold').fill('3')
  await page.getByRole('button', { name: 'Create product' }).click()
  await expect(page.getByText('Product created successfully.')).toBeVisible()
  await expect(page.getByText(sku, { exact: true })).toBeVisible()

  await page.getByRole('link', { name: 'Inventory' }).click()
  await page.getByRole('button', { name: 'Stock movement' }).click()
  await selectByText(page.getByLabel('Product'), new RegExp(sku))
  await selectByText(page.getByLabel('Warehouse'), /WAW-CENTRAL/)
  await page.getByLabel('Quantity').fill('12')
  await page.getByLabel('Reference').fill(`E2E-RECEIPT-${suffix}`)
  await page.getByRole('button', { name: 'Apply movement' }).click()
  await expect(page.getByRole('dialog')).toBeHidden()
  await page.getByPlaceholder('Search balances').fill(sku)
  const stockedRow = page.getByRole('row').filter({ hasText: sku }).filter({ hasText: 'WAW-CENTRAL' })
  await expect(stockedRow).toContainText('12 pcs')

  await page.getByRole('link', { name: 'Sales orders' }).click()
  await page.getByRole('button', { name: 'New sales order' }).click()
  await selectByText(page.getByLabel('Customer'), /CUS-NORTH/)
  await selectByText(page.getByLabel('Warehouse'), /WAW-CENTRAL/)
  await selectByText(page.getByLabel('Line 1 product'), new RegExp(sku))
  await page.getByLabel('Line 1 quantity').fill('2')
  await page.getByLabel('Notes').fill(`E2E sale ${suffix}`)
  const createdOrder = page.waitForResponse((response) =>
    response.url().endsWith('/api/v1/sales-orders') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'New sales order' }).last().click()
  const createResponse = await createdOrder
  expect(createResponse.ok()).toBeTruthy()
  const { order_number: orderNumber } = await createResponse.json() as { order_number: string }
  await expect(page.getByRole('dialog')).toBeHidden()

  const orderRow = page.getByRole('row').filter({ hasText: orderNumber })
  await orderRow.getByRole('button', { name: 'Confirm' }).click()
  await orderRow.getByRole('button', { name: 'Start processing' }).click()
  await orderRow.getByRole('button', { name: 'Complete' }).click()
  await expect(orderRow).toContainText('completed')

  await page.getByRole('link', { name: 'Inventory' }).click()
  await page.getByPlaceholder('Search balances').fill(sku)
  const fulfilledRow = page.getByRole('row').filter({ hasText: sku }).filter({ hasText: 'WAW-CENTRAL' })
  await expect(fulfilledRow).toContainText('10 pcs')

  await page.getByRole('link', { name: 'Audit log' }).click()
  await page.getByPlaceholder('Search action, entity, or request ID').fill('sales_order.complete')
  const auditRow = page.getByRole('row').filter({ hasText: 'sales_order.complete' }).first()
  await expect(auditRow).toContainText('success')
})

async function selectByText(select: Locator, pattern: RegExp): Promise<void> {
  const value = await select.locator('option').filter({ hasText: pattern }).first().getAttribute('value')
  if (!value) throw new Error(`No option matched ${pattern}`)
  await select.selectOption(value)
}
