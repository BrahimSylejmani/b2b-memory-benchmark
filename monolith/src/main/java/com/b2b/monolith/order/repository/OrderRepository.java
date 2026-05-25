package com.b2b.monolith.order.repository;

import com.b2b.monolith.order.entity.Order;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface OrderRepository extends JpaRepository<Order, Long> {
    List<Order> findByPartnerId(Long partnerId);
}
