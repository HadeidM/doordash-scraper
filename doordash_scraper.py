import requests
import json
import time
import csv
import collections


GRAPHQL_URL = "https://api-consumer-client.doordash.com/graphql"

ORDERS_QUERY = """
    query getConsumerOrdersWithDetails($offset: Int!, $limit: Int!, $includeCancelled: Boolean, $orderFilterType: OrderFilterType) {
      getConsumerOrdersWithDetails(
        offset: $offset
        limit: $limit
        includeCancelled: $includeCancelled
        orderFilterType: $orderFilterType
      ) {
        id
        orderUuid
        createdAt
        submittedAt
        store {
          id
          name
        }
        orders {
          id
          creator {
            id
            firstName
            lastName
          }
          items {
            id
            name
            quantity
            specialInstructions
            orderItemExtras {
              menuItemExtraId
              name
              orderItemExtraOptions {
                menuExtraOptionId
                name
                description
                price
                quantity
              }
            }
          }
        }
      }
    }
"""


class DoorDashScraper:
    def __init__(self, sessionid, verbose=False):
        if not sessionid:
            raise TypeError(
                "You must provide a sessionid. Log into doordash.com in a web browser and copy your sessionid cookie."
            )
        self.sessionid = sessionid
        self.verbose = verbose

    def session_cookie(self):
        # If the sessionid already contains semicolons, it's a full cookie string
        if ';' in self.sessionid:
            return self.sessionid
        # Otherwise, just the sessionid
        return f"sessionid={self.sessionid}"

    def log(self, *args, **kwargs):
        print(f"{time.ctime()}  ", *args, **kwargs)

    def fetch_orders(self, limit, offset):
        """Fetches one batch of orders, containing basic things like the date
        and store name but not a complete itemized receipt."""
        variables = {
            "limit": limit,
            "offset": offset,
            "includeCancelled": True,
            "orderFilterType": None
        }
        body = {"query": ORDERS_QUERY, "variables": variables, "operationName": "getConsumerOrdersWithDetails"}
        headers = {
            "cookie": self.session_cookie(),
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "content-type": "application/json",
            "accept": "*/*",
            "origin": "https://www.doordash.com",
            "referer": "https://www.doordash.com/consumer/order-history/"
        }
        r = requests.post(url=GRAPHQL_URL, json=body, headers=headers)
        data = json.loads(r.text)
        return data

    def fetch_orders_persisted(self, limit, offset):
        filename = f"doordash-orders-limit-{limit}-offset-{offset}.json"
        try:
            data = json.load(open(filename, "r"))
            return data, True
        except (IOError, ValueError):
            data = self.fetch_orders(limit, offset)
            json.dump(data, open(filename, "w"))
            return data, False

    def fetch_all_orders(self):
        """Fetches all orders in a loop."""
        limit = 20
        offset = 0
        self.log(f"Fetching all order summaries in batches of {limit}")
        while True:
            data, was_persisted = self.fetch_orders_persisted(limit, offset)
            if self.verbose:
                self.log(
                    f"Fetched orders from offset {offset}",
                    "(was persisted)" if was_persisted else "",
                )
            
            # Check for API errors
            if "errors" in data:
                error_msg = data["errors"][0]["message"] if data["errors"] else "Unknown error"
                self.log(f"API Error: {error_msg}")
                if self.verbose:
                    self.log(f"Full response: {json.dumps(data, indent=2)}")
                if "getConsumerOrdersWithDetails" in error_msg or "ordersHistory" in error_msg:
                    raise RuntimeError(
                        "DoorDash changed their order history GraphQL query. "
                        "Capture the new query from doordash.com (look for GraphQL calls in DevTools Network tab) "
                        "and update ORDERS_QUERY to match."
                    )
                raise RuntimeError(f"GraphQL API error: {error_msg}")
            
            # Check if data structure is as expected
            if "data" not in data:
                self.log(f"Unexpected response structure. Response keys: {list(data.keys())}")
                if self.verbose:
                    self.log(f"Full response: {json.dumps(data, indent=2)}")
                raise RuntimeError(f"Unexpected API response structure. Expected 'data' key but got: {list(data.keys())}")
            
            orders_history = data["data"].get("getConsumerOrdersWithDetails")

            if orders_history is None:
                self.log(
                    "Expected 'getConsumerOrdersWithDetails' in DoorDash GraphQL response but it was missing. "
                    "DoorDash likely changed the API again."
                )
                if self.verbose:
                    self.log(f"Full response: {json.dumps(data, indent=2)}")
                raise RuntimeError(
                    "DoorDash response did not include 'getConsumerOrdersWithDetails'. Update ORDERS_QUERY to match the current API."
                )
            if not orders_history:
                self.log("Got an empty batch, so we're done fetching order summaries!")
                break
            yield from orders_history
            offset += limit
            if not was_persisted:
                time.sleep(1)

    def fetch_receipt(self, order_id):
        """Fetches one full receipt which contains all the items that each person
        ordered. (DEPRECATED - no longer used with new API)"""
        url = (
            f"https://api.doordash.com/v2/order_carts/{order_id}/?expand=store_order_carts&expand=store_order_carts.%5Bdelivery%2Cstore%5D&expand=store_order_carts.store.business&expand=store_order_carts.orders.%5Bconsumer%5D&expand=store_order_carts.orders.order_items.%5Bitem%2Coptions%5D&expand=store_order_carts.orders.order_items.options.item_extra_option.item_extra&extra=is_group%2Csubtotal%2Ctax_amount%2Cdiscount_amount%2Cservice_fee%2Cdelivery_fee%2Cextra_sos_delivery_fee%2Cmin_order_fee%2Cmin_order_subtotal%2Cmin_age_requirement%2Cpromotions%2Cstore_order_carts%2Cdelivery_availability%2Ctip_suggestions%2Ccancelled_at%2Ctotal_charged%2Cis_pre_tippable%2Chide_sales_tax&extra=store_order_carts.%5Borders%2Cdelivery%2Ctip_amount%5D&extra=store_order_carts.orders.dd4b_expense_code&extra=store_order_carts.store.business&extra=store_order_carts.store.business.id&extra=store_order_carts.store.phone_number&extra=store_order_carts.delivery.%5Bstatus%2Cdelivery_address%2Cpickup_address%2Cdasher_approaching_customer_time%2Cdasher_at_store_time%2Cdasher_confirmed_time%2Cstore_confirmed_time%2Cdasher_location_available%2Cdasher_route_available%2Cshow_dynamic_eta%2Cdasher%2Cis_consumer_pickup%2Cis_ready_for_consumer_pickup%2Cfulfillment_type%2Chas_external_courier_tracking%2Cconsumer_poc_number%5D&extra=store_order_carts.delivery.pickup_address.id&extra=store_order_carts.delivery.pickup_address.address.printable_address&extra=store_order_carts.delivery.delivery_address.address.printable_address&extra=store_order_carts.orders.order_items&extra=store_order_carts.orders.order_items.%5Bid%2Cunit_price%2Cquantity%2Citem%2Csubstitution_preference%2Cspecial_instructions%2Coptions%5D&extra=store_order_carts.orders.order_items.options.%5Bid%2Citem_extra_option%5D&extra=store_order_carts.orders.order_items.options.item_extra_option.%5Bname%2Cdescription%2Cid%2Citem_extra%5D&extra=store_order_carts.orders.order_items.options.item_extra_option.item_extra.name&extra=store_order_carts.orders.order_items.item.%5Bname%2Cid%2Cprice%5D"
        )
        headers = {
            "cookie": self.session_cookie(),
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        r = requests.get(url, headers=headers)
        data = json.loads(r.text)
        return data

    def fetch_receipt_persisted(self, order_id):
        filename = f"doordash-receipt-id-{order_id}.json"
        try:
            data = json.load(open(filename, "r"))
            return data, True
        except (IOError, ValueError):
            data = self.fetch_receipt(order_id)
            json.dump(data, open(filename, "w"))
            return data, False

    def execute(self):
        rows = []
        for index, order_cart in enumerate(self.fetch_all_orders()):
            store_name = order_cart["store"]["name"]
            delivery_time = order_cart.get("submittedAt") or order_cart.get("createdAt")
            order_id = order_cart["orderUuid"] or order_cart["id"]
            
            # Validate that we have a timestamp, use default if missing
            if not delivery_time:
                self.log(f"Warning: Order {order_id} missing timestamp, using placeholder date")
                delivery_time = "1900-01-01T00:00:00Z"  # Sentinel date that parses correctly
            
            if self.verbose:
                self.log(f"Processing order {order_id} from {store_name} ({index})")
            
            # Process each sub-order (for group orders)
            for sub_order in order_cart["orders"]:
                creator = sub_order.get("creator")
                if creator:
                    first_name = creator.get("firstName") or "Unknown"
                    last_name = creator.get("lastName") or ""
                    person_name = f"{first_name} {last_name}".strip()
                else:
                    person_name = "Unknown"
                
                # Process each item in the order
                for item in sub_order["items"]:
                    item_name = item["name"]
                    options = []
                    
                    # Process item extras (options/modifiers)
                    for extra in item.get("orderItemExtras", []):
                        extra_name = extra["name"]
                        for extra_option in extra.get("orderItemExtraOptions", []):
                            option_name = extra_option["name"]
                            options.append((extra_name, option_name))
                    
                    option_strings = [f"{name}: {value}" for name, value in options]
                    options_string = ", ".join(option_strings)
                    
                    row = {
                        "order_id": order_id,
                        "date": delivery_time,
                        "store": store_name,
                        "person": person_name,
                        "item": item_name,
                        "options": options_string,
                    }
                    rows.append(row)
            
            time.sleep(0.1)  # Rate limiting

        # Write CSV
        filename = "doordash.csv"
        self.log("Writing normal CSV", filename)
        with open(filename, "w") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Date", "Store", "Person", "Item", "Options"])
            for row in rows:
                writer.writerow(
                    [
                        row["date"][:10],
                        row["store"],
                        row["person"],
                        row["item"],
                        row["options"],
                    ]
                )

        # Write pivoted CSV
        filename = "doordash-pivot.csv"
        self.log("Writing pivoted CSV", filename)
        by_order_id = collections.defaultdict(dict)
        for row in rows:
            order = by_order_id[row["order_id"]]
            order["date"] = row["date"]
            order["store"] = row["store"]
            order[row["person"]] = f"{row['item']}. {row['options']}"
        person_counter = collections.Counter()
        for row in rows:
            person_counter[row["person"]] += 1
        people = [person for person, _count in person_counter.most_common()]
        with open(filename, "w") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Date", "Store"] + people)
            for row in by_order_id.values():
                people_values = [row.get(person, "") for person in people]
                writer.writerow([row["date"][:10], row["store"]] + people_values)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "sessionid",
        help="your sessionid cookie value, or the full cookie string from Chrome DevTools Network tab",
    )
    parser.add_argument(
        "-v", "--verbose", help="show more detailed logs", action="store_true"
    )
    args = parser.parse_args()
    print(args.sessionid)

    scraper = DoorDashScraper(args.sessionid, args.verbose)
    scraper.execute()
