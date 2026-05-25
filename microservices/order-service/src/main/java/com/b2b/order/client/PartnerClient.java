package com.b2b.order.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

@FeignClient(name = "partner-service", url = "${partner.service.url}")
public interface PartnerClient {

    @GetMapping("/api/partners/{id}")
    Object getPartner(@PathVariable Long id);
}
